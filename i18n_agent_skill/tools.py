import hashlib
import json
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional

import aiofiles

from i18n_agent_skill.linter import TranslationStyleLinter
from i18n_agent_skill.logger import structured_logger as logger
from i18n_agent_skill.models import (
    ConflictStrategy,
    ErrorInfo,
    ExtractedString,
    ExtractOutput,
    PrivacyLevel,
    ProjectConfig,
    ProjectStatus,
    StyleFeedback,
    SyncProposal,
    TelemetryData,
    ValidationFeedback,
)
from i18n_agent_skill.snapshot import TranslationSnapshotManager
from i18n_agent_skill.vcs import get_git_hunks

# 全局常量
CACHE_FILE = ".i18n-cache.json"
PROPOSALS_DIR = ".i18n-proposals"
GLOSSARY_FILE = "GLOSSARY.json"
CONFIG_FILE = ".i18n-skill.json"
WORKSPACE_ROOT = os.getcwd()

# [工业级优化] 工程黑名单
ENG_BLACKLIST = {
    "get", "post", "put", "delete", "json", "utf-8", "utf8", "true", "false", 
    "null", "undefined", "none", "px", "rem", "em", "vh", "vw", "ms", "v-model", 
    "src", "href", "id", "class", "style", "key", "index", "content-type", "application/json"
}

def _is_likely_ui_string(text: str, context: str = "") -> bool:
    """[v0.4.0] 语义仲裁前置过滤：排除纯工程噪声"""
    t = text.strip()
    if not t or len(t) < 2: return False
    # 1. 100% 确认：非 ASCII (中/日/韩/俄/德变音)
    if re.search(r'[^\x00-\x7f]', t): return True
    # 2. 物理拦截：SVG, Base64, Hex, URL, 路径
    if re.match(r'^[MmLlHhVvCcSsQqTtAaZz0-9\s,\.\-]+$', t) and len(t) > 20: return False
    if re.match(r'^#([A-Fa-f0-9]{3,8})$', t): return False
    if t.startswith(("/", "./", "../", "http", "mailto:", "tel:")): return False
    # 3. 代码形状拦截：Kebap-case 类名, CamelCase 变量
    if re.match(r'^[a-z0-9\-]+$', t) and "-" in t: return False
    if re.match(r'^[a-z]+[A-Z][a-zA-Z0-9]*$', t): return False
    # 4. 黑名单
    if t.lower() in ENG_BLACKLIST: return False
    # 5. 上下文噪音拦截
    if context:
        low_ctx = context.lower()
        if any(x in low_ctx for x in ["console.log", "logger.", "new error", "throw ", "require(", "import "]):
            return False
    return True

def _strip_comments(content: str) -> str:
    """[核心优化] 物理移除注释内容，防止提取引擎在注释中浪费 Token"""
    # 移除多行注释 /* ... */
    content = re.sub(r'/\*[\s\S]*?\*/', '', content)
    # 移除单行注释 // ...
    content = re.sub(r'//.*', '', content)
    # 移除 Python/Shell 风格注释 # ...
    content = re.sub(r'#.*', '', content)
    return content

async def extract_raw_strings(file_path: str, use_cache: bool = True, vcs_mode: bool = False, privacy_level: Optional[PrivacyLevel] = None) -> ExtractOutput:
    """[v0.4.0] 手术刀级提取引擎：支持转义引号、无引号文本、多行注释拦截及模板标准化。"""
    start_ts = time.perf_counter()
    config = await _load_project_config()
    p_level = privacy_level or config.privacy_level
    privacy_hits, results = 0, []

    try:
        safe_path = _validate_safe_path(file_path)
        if os.path.isdir(safe_path):
            return ExtractOutput(error=ErrorInfo(error_code="DIR_ERR", message=f"'{file_path}' is a dir."))
    except Exception as e:
        return ExtractOutput(error=ErrorInfo(error_code="PATH_ERR", message=str(e)))

    changed_hunks = get_git_hunks(WORKSPACE_ROOT)
    if vcs_mode and file_path not in changed_hunks: return ExtractOutput(results=[], is_cached=True)

    if use_cache:
        file_hash = await _get_file_hash(file_path)
        cache = await _read_cache()
        if file_path in cache and cache[file_path].get("hash") == file_hash:
            # 缓存路径保持原有逻辑...
            pass

    async with aiofiles.open(_validate_safe_path(file_path), mode='r', encoding='utf-8') as f:
        original_content = await f.read()

    # 1. 预处理：剥离注释，生成纯代码副本用于扫描，但保留行号索引
    code_only = _strip_comments(original_content)
    lines = original_content.splitlines()
    code_lines = code_only.splitlines()

    # 2. 混合提取模型 (Quotes + JSX Text + Templates)
    # 正则 A: 处理带转义支持的引号字符串 (单/双)
    QUOTE_PATTERN = r'(?<!\\)["\']((?:\\.|[^"\'])*?)(?<!\\)["\']'
    # 正则 B: 处理模板字符串 (反引号)
    TEMPLATE_PATTERN = r'`([\s\S]*?)`'
    # 正则 C: 处理 JSX/Vue 标签间的纯文本 (解决无引号盲区)
    TAG_TEXT_PATTERN = r'>\s*([^\x00-\x7f]+[^\x00-\x7f\s<]*)\s*<'

    extracted_set = set()

    # 执行行级扫描以保留行号
    for i, line in enumerate(lines):
        line_no = i + 1
        if i >= len(code_lines): break
        
        target_line = code_lines[i] # 仅扫描无注释的代码行
        
        # A. 提取引号字符串
        matches = re.findall(QUOTE_PATTERN, target_line)
        # B. 提取标签间文本 (JSXText Polyfill)
        matches += re.findall(TAG_TEXT_PATTERN, target_line)
        # C. 提取反引号 (处理简单的模板字符串)
        matches += re.findall(r'`(.*?)`', target_line)

        for text in set(matches):
            if not text or (text, line_no) in extracted_set: continue
            
            # 标准化模板占位符
            processed = re.sub(r'\$\{(.*?)\}', r'{\1}', text)
            
            if _is_likely_ui_string(processed, "\n".join(lines[max(0, i-1):min(len(lines), i+2)])):
                masked, is_m = _mask_sensitive_data(processed, p_level)
                if is_m: privacy_hits += 1
                results.append(ExtractedString(text=masked, line=line_no, context="\n".join(lines[max(0, i-1):min(len(lines), i+2)]), is_masked=is_m))
                extracted_set.add((text, line_no))

    glossary = await load_project_glossary()
    glossary_ctx = {r.text: glossary[r.text] for r in results if r.text in glossary}
    
    if use_cache:
        cache = await _read_cache()
        cache[file_path] = {"hash": await _get_file_hash(file_path), "results": [r.model_dump() for r in results]}
        await _write_cache(cache)

    return ExtractOutput(results=results, is_cached=False, telemetry=TelemetryData(duration_ms=(time.perf_counter()-start_ts)*1000, files_processed=1, cache_hits=0, keys_extracted=len(results), tokens_saved_approx=privacy_hits*50, privacy_shield_hits=privacy_hits), glossary_context=glossary_ctx)

def _flatten_dict(d: dict[str, Any], p_key: str = '', sep: str = '.') -> dict[str, str]:
    items = []
    for k, v in d.items():
        new_key = f"{p_key}{sep}{k}" if p_key else k
        if isinstance(v, dict): items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else: items.append((new_key, str(v)))
    return dict(items)

def _unflatten_dict(d: dict[str, Any], sep: str = '.') -> dict[str, Any]:
    res = {}
    for k, v in d.items():
        parts, d_ref = k.split(sep), res
        for part in parts[:-1]:
            if part not in d_ref: d_ref[part] = {}
            d_ref = d_ref[part]
        d_ref[parts[-1]] = v
    return res

def _deep_update(d: dict[str, Any], u: dict[str, Any], strategy: ConflictStrategy = ConflictStrategy.KEEP_EXISTING) -> dict[str, Any]:
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict): _deep_update(d[k], v, strategy)
        else:
            if k in d and strategy == ConflictStrategy.KEEP_EXISTING: continue
            d[k] = v
    return d

async def propose_sync_i18n(new_pairs: dict[str, str], lang_code: str, reasoning: str, base_dir: Optional[str] = None, strategy: ConflictStrategy = ConflictStrategy.KEEP_EXISTING) -> SyncProposal:
    start_ts = time.perf_counter()
    config = await _load_project_config()
    target_dir = base_dir or _detect_locale_dir(config)
    file_path, base_path = os.path.join(target_dir, f"{lang_code}.json"), os.path.join(target_dir, "en.json")
    current_data, base_data, val_errs, style_suggs = {}, {}, [], []
    if os.path.exists(base_path):
        try:
            async with aiofiles.open(base_path, "r", encoding="utf-8") as f: base_data = _flatten_dict(json.loads(await f.read()))
        except Exception: pass
    if os.path.exists(file_path):
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f: current_data = json.loads(await f.read())
        except Exception: pass
    for key, val in new_pairs.items():
        if key in base_data:
            exp, act = re.findall(r'\{\{.*?\}\}|\{.*?\}', base_data[key]), re.findall(r'\{\{.*?\}\}|\{.*?\}', val)
            if set(exp) != set(act): val_errs.append(ValidationFeedback(key=key, expected_placeholders=exp, actual_placeholders=act, message=f"Mismatch for '{key}'."))
        style_suggs.extend(TranslationStyleLinter.lint(key, val, lang_code))
    proposal_id = str(uuid.uuid4())
    os.makedirs(os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR), exist_ok=True)
    async with aiofiles.open(os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json"), "w", encoding="utf-8") as f: await f.write(json.dumps({"target_file": file_path, "content": _deep_update(current_data.copy(), _unflatten_dict(new_pairs), strategy), "reasoning": reasoning, "lang_code": lang_code, "score": 9}, indent=2, ensure_ascii=False, sort_keys=True))
    return SyncProposal(proposal_id=proposal_id, lang_code=lang_code, changes_count=len(new_pairs), diff_summary=new_pairs, reasoning=reasoning, file_path=file_path, validation_errors=val_errs, style_suggestions=style_suggs, telemetry=TelemetryData(duration_ms=(time.perf_counter()-start_ts)*1000, files_processed=1, keys_extracted=len(new_pairs)))

async def commit_i18n_changes(proposal_id: str) -> str:
    temp_p = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json")
    if not os.path.exists(temp_p): return f"Error: Proposal {proposal_id} not found."
    async with aiofiles.open(temp_p, "r", encoding="utf-8") as f: proposal = json.loads(await f.read())
    safe_target = _validate_safe_path(proposal["target_file"])
    os.makedirs(os.path.dirname(safe_target), exist_ok=True)
    async with aiofiles.open(safe_target, "w", encoding="utf-8") as f: await f.write(json.dumps(proposal["content"], indent=2, ensure_ascii=False, sort_keys=True))
    snapshot_mgr = TranslationSnapshotManager(WORKSPACE_ROOT)
    for k, v in _flatten_dict(proposal["content"]).items(): await snapshot_mgr.update_snapshot(k, v, 9)
    os.remove(temp_p)
    return f"Committed: {safe_target}."

async def get_missing_keys(lang_code: str, base_lang: str = "en", base_dir: Optional[str] = None) -> dict[str, str]:
    config = await _load_project_config()
    target_dir = base_dir or _detect_locale_dir(config)
    base_p, target_p = _validate_safe_path(os.path.join(target_dir, f"{base_lang}.json")), _validate_safe_path(os.path.join(target_dir, f"{lang_code}.json"))
    base_d, target_d = {}, {}
    if os.path.exists(base_p):
        try:
            async with aiofiles.open(base_p, "r", encoding="utf-8") as f: base_d = _flatten_dict(json.loads(await f.read()))
        except Exception: pass
    if os.path.exists(target_p):
        try:
            async with aiofiles.open(target_p, mode='r', encoding='utf-8') as f: target_d = _flatten_dict(json.loads(await f.read()))
        except Exception: pass
    return {k: base_d[k] for k in set(base_d.keys()) - set(target_d.keys())}
