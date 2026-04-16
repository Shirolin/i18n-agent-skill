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

def _is_likely_ui_string(text: str, source_type: str) -> bool:
    """[v0.6.0] 语义前置过滤：区分自然语言与工程噪声"""
    t = text.strip()
    if not t or len(t) < 2: return False
    # 1. 物理放行：包含非 ASCII (中/日/韩/俄/德变音) 100% 是 UI
    if re.search(r'[^\x00-\x7f]', t):
        # 排除纯标点
        if not re.search(r'[\w\u4e00-\u9fa5\u3040-\u30ff]', t): return False
        return True
    
    # 2. 结构放行：如果是标签间的纯文本 (TEXT_NODE)，即便很短大概率也是 UI
    if source_type == "TEXT_NODE":
        if re.match(r'^[A-Z][a-z]+$', t): return True # "Save", "Add"
        if " " in t: return True
        return len(t) > 3

    # 3. 拦截：排除明显的代码特征
    if re.match(r'^[a-z0-9\-]+$', t) and ("-" in t): return False # CSS 类名
    if re.match(r'^[a-z]+[A-Z][a-zA-Z0-9]*$', t): return False # CamelCase 变量
    if t.startswith(("/", "./", "http", "tel:", "mailto:")): return False
    
    # 4. 黑名单过滤
    if t.lower() in {"id", "class", "style", "key", "v-model", "json", "utf-8"}: return False

    return " " in t or t[0].isupper() or re.search(r'[.!?:]$', t)

def _scanner(content: str):
    """[v0.6.0] 流式扫描器：通过有限状态机(FSM)物理隔离注释，支持转义与无引号文本。"""
    i, n = 0, len(content)
    line_no = 1
    
    while i < n:
        char = content[i]
        
        # 1. 处理换行
        if char == '\n':
            line_no += 1
            i += 1
            continue
            
        # 2. 处理注释（物理跳过，不伤及字符串内的 //）
        if char == '/' and i + 1 < n:
            if content[i+1] == '/': # 行注释
                while i < n and content[i] != '\n': i += 1
                continue
            if content[i+1] == '*': # 块注释
                i += 2
                while i + 1 < n and not (content[i] == '*' and content[i+1] == '/'):
                    if content[i] == '\n': line_no += 1
                    i += 1
                i += 2
                continue

        # 3. 处理引号字符串 (', ") - 支持转义
        if char in ("'", '"'):
            quote_type = char
            i += 1
            text = ""
            while i < n:
                if content[i] == '\\' and i + 1 < n: # 处理转义
                    text += content[i:i+2]
                    i += 2
                    continue
                if content[i] == quote_type:
                    yield "STRING", text, line_no
                    i += 1
                    break
                if content[i] == '\n': line_no += 1
                text += content[i]
                i += 1
            continue

        # 4. 处理模板字符串 (`)
        if char == '`':
            i += 1
            text = ""
            while i < n:
                if content[i] == '`':
                    yield "TEMPLATE", text, line_no
                    i += 1
                    break
                if content[i] == '\n': line_no += 1
                text += content[i]
                i += 1
            continue

        # 5. 处理标签间文本节点 (JSX/Vue Text) - 解决无引号盲区
        if char == '>':
            i += 1
            text = ""
            start_line = line_no
            while i < n and content[i] != '<':
                if content[i] == '\n': line_no += 1
                text += content[i]
                i += 1
            # 过滤掉明显的逻辑括号块
            t_strip = text.strip()
            if t_strip and not t_strip.startswith(('{', '}', '(', ')')):
                yield "TEXT_NODE", t_strip, start_line
            continue

        i += 1

async def extract_raw_strings(file_path: str, use_cache: bool = True, vcs_mode: bool = False, privacy_level: Optional[PrivacyLevel] = None) -> ExtractOutput:
    """[v0.6.0] 架构级重构：模拟 AST 的分词提取引擎。"""
    start_ts = time.perf_counter()
    config = await _load_project_config()
    p_level = privacy_level or config.privacy_level
    privacy_hits, results = 0, []

    try:
        safe_p = _validate_safe_path(file_path)
        if os.path.isdir(safe_p): return ExtractOutput(error=ErrorInfo(error_code="DIR_ERR", message="Folder scan not supported."))
        async with aiofiles.open(safe_p, mode='r', encoding='utf-8') as f:
            content = await f.read()
    except Exception as e:
        return ExtractOutput(error=ErrorInfo(error_code="READ_ERR", message=str(e)))

    all_lines = content.splitlines()
    extracted_keys = set()
    
    for stype, text, line in _scanner(content):
        # 标准化占位符
        processed = re.sub(r'\$\{(.*?)\}', r'{\1}', text) if stype == "TEMPLATE" else text
        
        if _is_likely_ui_string(processed, stype):
            if (processed, line) in extracted_keys: continue
            
            ctx = "\n".join(all_lines[max(0, line-2):min(len(all_lines), line+1)])
            masked, is_m = _mask_sensitive_data(processed, p_level)
            if is_m: privacy_hits += 1
            results.append(ExtractedString(text=masked, line=line, context=ctx, is_masked=is_m))
            extracted_keys.add((processed, line))

    glossary = await load_project_glossary()
    glossary_ctx = {r.text: glossary[r.text] for r in results if r.text in glossary}
    
    return ExtractOutput(results=results, is_cached=False, telemetry=TelemetryData(duration_ms=(time.perf_counter()-start_ts)*1000, files_processed=1, keys_extracted=len(results), privacy_shield_hits=privacy_hits), glossary_context=glossary_ctx)

def _validate_safe_path(path: str) -> str:
    ws_root = os.path.normpath(os.path.abspath(WORKSPACE_ROOT)).lower()
    target_path = os.path.normpath(os.path.abspath(os.path.join(WORKSPACE_ROOT, path)))
    if not target_path.lower().startswith(ws_root): raise PermissionError("Outside workspace.")
    return target_path

async def _load_project_config() -> ProjectConfig:
    config_path = os.path.join(WORKSPACE_ROOT, CONFIG_FILE)
    if not os.path.exists(config_path): return ProjectConfig()
    try:
        async with aiofiles.open(config_path, "r", encoding="utf-8") as f: return ProjectConfig(**json.loads(await f.read()))
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
    return ProjectStatus(config=config, has_glossary=os.path.exists(os.path.join(WORKSPACE_ROOT, GLOSSARY_FILE)), cache_size=0, workspace_root=WORKSPACE_ROOT, status_message="Ready.", vcs_info=None)

async def load_project_glossary() -> Dict[str, str]:
    path = os.path.join(WORKSPACE_ROOT, GLOSSARY_FILE)
    if not os.path.exists(path): return {}
    try:
        async with aiofiles.open(path, "r", encoding="utf-8") as f: return json.loads(await f.read())
    except: return {}

async def update_project_glossary(term: str, translation: str) -> str:
    glossary = await load_project_glossary()
    glossary[term] = translation
    async with aiofiles.open(os.path.join(WORKSPACE_ROOT, GLOSSARY_FILE), "w", encoding="utf-8") as f:
        await f.write(json.dumps(glossary, indent=2, ensure_ascii=False, sort_keys=True))
    return f"Learned: {term}"

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
    except: return {}

async def _write_cache(cache: Dict[str, Any]) -> None:
    async with aiofiles.open(os.path.join(WORKSPACE_ROOT, CACHE_FILE), "w", encoding="utf-8") as f:
        await f.write(json.dumps(cache, indent=2, ensure_ascii=False))

async def propose_sync_i18n(new_pairs: dict[str, str], lang_code: str, reasoning: str, base_dir: Optional[str] = None, strategy: ConflictStrategy = ConflictStrategy.KEEP_EXISTING) -> SyncProposal:
    start_ts = time.perf_counter()
    config = await _load_project_config()
    target_dir = base_dir or _detect_locale_dir(config)
    file_path = os.path.join(target_dir, f"{lang_code}.json")
    proposal_id = str(uuid.uuid4())
    os.makedirs(os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR), exist_ok=True)
    async with aiofiles.open(os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json"), "w", encoding="utf-8") as f:
        await f.write(json.dumps({"target_file": file_path, "content": new_pairs, "reasoning": reasoning, "lang_code": lang_code}, indent=2, ensure_ascii=False))
    return SyncProposal(proposal_id=proposal_id, lang_code=lang_code, changes_count=len(new_pairs), diff_summary=new_pairs, reasoning=reasoning, file_path=file_path)

async def commit_i18n_changes(proposal_id: str) -> str:
    temp_p = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json")
    if not os.path.exists(temp_p): return "Proposal not found."
    async with aiofiles.open(temp_p, "r", encoding="utf-8") as f: data = json.loads(await f.read())
    async with aiofiles.open(data["target_file"], "w", encoding="utf-8") as f:
        await f.write(json.dumps(data["content"], indent=2, ensure_ascii=False, sort_keys=True))
    os.remove(temp_p)
    return "Committed."

async def get_missing_keys(lang_code: str, base_lang: str = "en", base_dir: Optional[str] = None) -> dict[str, str]:
    config = await _load_project_config()
    target_dir = base_dir or _detect_locale_dir(config)
    base_p, target_p = os.path.join(target_dir, f"{base_lang}.json"), os.path.join(target_dir, f"{lang_code}.json")
    try:
        async with aiofiles.open(base_p, "r", encoding="utf-8") as f: b_d = json.loads(await f.read())
        async with aiofiles.open(target_p, "r", encoding="utf-8") as f: t_d = json.loads(await f.read())
    except: return {}
    return {k: v for k, v in b_d.items() if k not in t_d}
