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

# [深度优化] 工程级黑名单：常见不需要翻译的逻辑 Token
ENG_BLACKLIST = {
    "get", "post", "put", "delete", "json", "utf-8", "utf8", "true", "false", 
    "null", "undefined", "none", "px", "rem", "em", "vh", "vw", "ms", "v-model", 
    "src", "href", "id", "class", "style", "key", "index", "content-type"
}

def _is_likely_ui_string(text: str, context: str = "") -> bool:
    """
    [深度精度重构] 高阶启发式过滤：利用语义、形状及黑名单精确识别 UI 文案。
    """
    # 1. 基础清理
    t = text.strip()
    if not t: return False

    # 2. 物理防线：包含非 ASCII 字符（日语、中文等）必然是 UI
    if re.search(r'[^\x00-\x7f]', t):
        return True
    
    # 3. 格式拦截：剔除常见的非自然语言模式
    # - SVG 路径 (通常以 M, m, L, l 开始)
    if re.match(r'^[MmLlHhVvCcSsQqTtAaZz0-9\s,\.\-]+$', t) and len(t) > 20: return False
    # - 十六进制颜色与 Base64
    if re.match(r'^#([A-Fa-f0-9]{3,8})$', t): return False
    if len(t) > 30 and re.match(r'^[A-Za-z0-9+/=]+$', t) and not " " in t: return False
    # - 常见的路径与 URL
    if t.startswith(("/", "./", "../", "http://", "https://", "mailto:", "tel:")): return False
    # - 常见的 CSS 类名 (Kebap-case)
    if re.match(r'^[a-z0-9\-]+$', t) and "-" in t: return False
    # - 驼峰变量名 (CamelCase)
    if re.match(r'^[a-z]+[A-Z][a-zA-Z0-9]*$', t): return False

    # 4. 上下文防线：忽略特定的代码调用
    if context:
        # 忽略打印、日志、错误抛出、及特定的非 UI 属性定义
        lower_ctx = context.lower()
        if any(kw in lower_ctx for kw in ["console.log", "logger.", "new error", "throw ", "require(", "import "]):
            return False

    # 5. 黑名单防线
    if t.lower() in ENG_BLACKLIST: return False

    # 6. 自然语言特征提取
    # - 包含空格 (句子特征)
    if " " in t: return True
    # - 包含结尾标点
    if re.search(r'[.!?]$', t): return True
    # - 首字母大写且非全大写 (Button / Label 特征)
    if t[0].isupper() and not t.isupper(): return True
    # - 足够长的英文字符串（如警告语）
    if len(t) > 15 and not re.search(r'[^a-zA-Z\s,.]', t): return True
        
    return False


def _convert_template_to_placeholders(text: str) -> str:
    """将 ES6 模板字符串中的 ${var} 转换为国际化标准的 {var} 占位符"""
    return re.sub(r'\$\{(.*?)\}', r'{\1}', text)


def _mask_sensitive_data(text: str, level: PrivacyLevel) -> tuple[str, bool]:
    if level == PrivacyLevel.OFF: return text, False
    masked_text, is_masked = text, False
    patterns_to_check = ["EMAIL", "API_KEY"] if level == PrivacyLevel.BASIC else list(SENSITIVE_PATTERNS.keys())
    for p_type in patterns_to_check:
        pattern = SENSITIVE_PATTERNS[p_type]
        if re.search(pattern, masked_text, re.IGNORECASE):
            masked_text, count = re.subn(pattern, f"[MASKED_{p_type}]", masked_text, flags=re.IGNORECASE)
            if count > 0: is_masked = True
    return masked_text, is_masked


def _validate_safe_path(path: str) -> str:
    ws_root = os.path.normpath(os.path.abspath(WORKSPACE_ROOT)).lower()
    target_path = os.path.normpath(os.path.abspath(os.path.join(WORKSPACE_ROOT, path)))
    if not target_path.lower().startswith(ws_root):
        raise PermissionError(f"Access Denied: '{path}' is outside workspace.")
    return target_path


async def _load_project_config() -> ProjectConfig:
    config_path = os.path.join(WORKSPACE_ROOT, CONFIG_FILE)
    if not os.path.exists(config_path): return ProjectConfig()
    try:
        async with aiofiles.open(config_path, "r", encoding="utf-8") as f:
            return ProjectConfig(**json.loads(await f.read()))
    except Exception: return ProjectConfig()


async def check_project_status() -> ProjectStatus:
    config = await _load_project_config()
    locales_dir = _detect_locale_dir(config)
    full_locales_path = os.path.join(WORKSPACE_ROOT, locales_dir)
    detected_langs = []
    if os.path.exists(full_locales_path):
        detected_langs = [f.replace(".json", "") for f in os.listdir(full_locales_path) if f.endswith(".json")]
    if len(detected_langs) > 0:
        current_langs = set(config.enabled_langs)
        for lang in detected_langs:
            if lang not in current_langs: config.enabled_langs.append(lang)
    cache = await _read_cache()
    hunks = get_git_hunks(WORKSPACE_ROOT)
    vcs_info = {"git_available": True, "changed_files_count": len(hunks), "hunk_details": {f: list(lines) for f, lines in hunks.items()}}
    return ProjectStatus(config=config, has_glossary=os.path.exists(os.path.join(WORKSPACE_ROOT, GLOSSARY_FILE)), cache_size=len(cache), workspace_root=WORKSPACE_ROOT, status_message=f"Ready. Privacy Shield: {config.privacy_level}", vcs_info=vcs_info)


async def load_project_glossary() -> Dict[str, str]:
    glossary_path = os.path.join(WORKSPACE_ROOT, GLOSSARY_FILE)
    if not os.path.exists(glossary_path): return {}
    try:
        async with aiofiles.open(glossary_path, "r", encoding="utf-8") as f: return json.loads(await f.read())
    except Exception: return {}


async def update_project_glossary(term: str, translation: str) -> str:
    glossary = await load_project_glossary()
    glossary[term] = translation
    async with aiofiles.open(os.path.join(WORKSPACE_ROOT, GLOSSARY_FILE), "w", encoding="utf-8") as f:
        await f.write(json.dumps(glossary, indent=2, ensure_ascii=False, sort_keys=True))
    return f"Learned: '{term}' -> '{translation}'"


def _detect_locale_dir(config: Optional[ProjectConfig] = None) -> str:
    if config and config.locales_dir != "locales": return config.locales_dir
    for candidate in ["locales", os.path.join("src", "locales")]:
        if os.path.isdir(os.path.join(WORKSPACE_ROOT, candidate)): return candidate
    return "locales"


async def _get_file_hash(file_path: str) -> str:
    hash_md5 = hashlib.md5()
    async with aiofiles.open(_validate_safe_path(file_path), "rb") as f:
        while chunk := await f.read(4096): hash_md5.update(chunk)
    return hash_md5.hexdigest()


async def _read_cache() -> Dict[str, Any]:
    cache_path = os.path.join(WORKSPACE_ROOT, CACHE_FILE)
    if not os.path.exists(cache_path): return {}
    try:
        async with aiofiles.open(cache_path, "r", encoding="utf-8") as f: return json.loads(await f.read())
    except Exception: return {}


async def _write_cache(cache: Dict[str, Any]) -> None:
    async with aiofiles.open(os.path.join(WORKSPACE_ROOT, CACHE_FILE), "w", encoding="utf-8") as f:
        await f.write(json.dumps(cache, indent=2, ensure_ascii=False))


async def extract_raw_strings(file_path: str, use_cache: bool = True, vcs_mode: bool = False, privacy_level: Optional[PrivacyLevel] = None) -> ExtractOutput:
    """深度精度提取引擎：支持模板字符串感知、全语言识别、及工程语义过滤。"""
    start_ts = time.perf_counter()
    config = await _load_project_config()
    p_level = privacy_level or config.privacy_level
    privacy_shield_hits, results = 0, []

    try:
        safe_path = _validate_safe_path(file_path)
        if os.path.isdir(safe_path):
            return ExtractOutput(error=ErrorInfo(error_code="DIRECTORY_NOT_SUPPORTED", message=f"Path '{file_path}' is a directory.", suggested_action="Scan files individually."))
    except Exception as e:
        return ExtractOutput(error=ErrorInfo(error_code="PATH_ERROR", message=str(e), suggested_action="Verify path."))

    changed_hunks = get_git_hunks(WORKSPACE_ROOT)
    if vcs_mode and file_path not in changed_hunks: return ExtractOutput(results=[], is_cached=True)
    target_lines = changed_hunks.get(file_path) if vcs_mode else None

    if use_cache:
        file_hash = await _get_file_hash(file_path)
        cache = await _read_cache()
        if file_path in cache and cache[file_path].get("hash") == file_hash:
            cached_raw = cache[file_path].get("results", [])
            for r in cached_raw:
                if target_lines and r.get("line") not in target_lines: continue
                masked_text, is_masked = _mask_sensitive_data(r["text"], p_level)
                if is_masked: privacy_shield_hits += 1
                results.append(ExtractedString(text=masked_text, line=r["line"], context=r["context"], is_masked=is_masked))
            glossary = await load_project_glossary()
            glossary_ctx = {r.text: glossary[r.text] for r in results if r.text in glossary}
            return ExtractOutput(results=results, is_cached=True, telemetry=TelemetryData(duration_ms=(time.perf_counter()-start_ts)*1000, files_processed=1, cache_hits=1, keys_extracted=len(results), tokens_saved_approx=len(results)*20, privacy_shield_hits=privacy_shield_hits), glossary_context=glossary_ctx)

    async with aiofiles.open(_validate_safe_path(file_path), mode='r', encoding='utf-8') as f:
        lines = (await f.read()).splitlines()

    # [深度精度优化] 正则升级：支持单引号、双引号及反引号（模板字符串）
    STRING_PATTERN = r'["\'](.*?)["\']|`(.*?)`'

    for i, line in enumerate(lines):
        line_no = i + 1
        if target_lines and line_no not in target_lines: continue
        stripped = line.strip()
        if stripped.startswith(("//", "/*", "*", "#")): continue
        
        matches = re.findall(STRING_PATTERN, line)
        for m_tuple in matches:
            # 找到非空的捕获组
            text = m_tuple[0] or m_tuple[1]
            if not text: continue
            
            # [核心优化] 提取前预处理模板字符串
            processed_text = _convert_template_to_placeholders(text)
            
            # [核心优化] 启发式 UI 文案精准识别
            context_fragment = "\n".join(lines[max(0, i-1):min(len(lines), i+2)])
            if not _is_likely_ui_string(processed_text, context_fragment): continue
            
            masked_text, is_masked = _mask_sensitive_data(processed_text, p_level)
            if is_masked: privacy_shield_hits += 1
            results.append(ExtractedString(text=masked_text, line=line_no, context=context_fragment, is_masked=is_masked))

    glossary = await load_project_glossary()
    glossary_ctx = {r.text: glossary[r.text] for r in results if r.text in glossary}
    if use_cache:
        cache = await _read_cache()
        cache[file_path] = {"hash": await _get_file_hash(file_path), "results": [r.model_dump() for r in results]}
        await _write_cache(cache)

    return ExtractOutput(results=results, is_cached=False, telemetry=TelemetryData(duration_ms=(time.perf_counter()-start_ts)*1000, files_processed=1, cache_hits=0, keys_extracted=len(results), tokens_saved_approx=privacy_shield_hits*50, privacy_shield_hits=privacy_shield_hits), glossary_context=glossary_ctx)


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
