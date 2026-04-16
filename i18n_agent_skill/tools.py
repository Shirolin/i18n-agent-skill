import hashlib
import json
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Set

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

# 工程噪声拦截 (针对 ASCII 字符串)
ENG_NOISE_PATTERNS = [
    r'^[a-z0-9\-]+$',                   # Kebap-case (CSS)
    r'^[a-z]+[A-Z][a-zA-Z0-9]*$',       # CamelCase (Variables)
    r'^#([A-Fa-f0-9]{3,8})$',           # Colors
    r'^[MmLlHhVvCcSsQqTtAaZz0-9\s,\.\-]+$', # SVG
    r'^[A-Za-z0-9+/=]+$',               # Base64
    r'^(?:https?|ftp|tel|mailto):',     # Protocols
    r'^/|^\./|^\.\./'                   # Paths
]

UI_ATTRS = {"placeholder", "title", "label", "aria-label", "alt", "value"}

def _is_likely_ui(text: str, origin: str) -> bool:
    """[v1.0] 全球化 UI 文案判定逻辑。"""
    t = text.strip()
    if not t or len(t) < 2: return False
    
    # 1. 物理放行：非 ASCII (日语/中文/法语变音等) -> 100% 提取
    if re.search(r'[^\x00-\x7f]', t):
        return bool(re.search(r'[\w\u4e00-\u9fa5\u3040-\u30ff]', t))
    
    # 2. 来源补偿：如果是标签间文本或专用属性 -> 高召回 (处理短英文)
    if origin in ("text_node", "ui_attr"):
        if re.match(r'^[0-9\s.,:\-_]+$', t): return False
        return True
    
    # 3. 代码字符串 -> 高精过滤
    if " " in t or re.search(r'[.!?:]$', t): return True
    if t[0].isupper() and not t.isupper() and len(t) > 2: return True
    
    return False

def _lex_scan(content: str):
    """[v1.0] 词法扫描器：互斥捕获 注释/属性/文本/引号。"""
    # 1. 注释 (Skip) | 2. 属性 (attr=val) | 3. 文本节点 (>Text<) | 4. 引号字符串 | 5. 模板字符串
    PATTERN = r'(?m)' \
              r'(//.*|/\*[\s\S]*?\*/)|' \
              r'(\w+)=["\']((?:\\.|[^"\'])*?)["\']|' \
              r'>\s*([^<>\r\n]+?)\s*<|' \
              r'["\']((?:\\.|[^"\'])*?)["\']|' \
              r'`([\s\S]*?)`'
              
    for m in re.finditer(PATTERN, content):
        if m.group(1): continue # 注释
        
        start_pos = m.start()
        line_no = content.count('\n', 0, start_pos) + 1
        
        if m.group(2) and m.group(3): # Attributes
            attr = m.group(2).lower()
            yield (m.group(3), "ui_attr" if attr in UI_ATTRS else "code", line_no)
        elif m.group(4): # Text Node
            yield (m.group(4).strip(), "text_node", line_no)
        elif m.group(5) or m.group(6): # Strings
            yield (m.group(5) or m.group(6), "code", line_no)

async def extract_raw_strings(file_path: str, use_cache: bool = True, vcs_mode: bool = False, privacy_level: Optional[PrivacyLevel] = None) -> ExtractOutput:
    """[v1.0 Final] 来源感知型全球化提取引擎。"""
    start_ts = time.perf_counter()
    config = await _load_project_config()
    p_level = privacy_level or config.privacy_level
    privacy_hits, results = 0, []

    try:
        safe_p = _validate_safe_path(file_path)
        async with aiofiles.open(safe_p, mode='r', encoding='utf-8') as f:
            content = await f.read()
    except Exception as e:
        return ExtractOutput(error=ErrorInfo(error_code="IO_ERR", message=str(e)))

    lines = content.splitlines()
    extracted_set: Set[tuple] = set()
    
    for text, origin, line in _lex_scan(content):
        if not text: continue
        
        # 模板变量标准化处理
        processed = re.sub(r'\$\{(.*?)\}', r'{\1}', text)
        
        if _is_likely_ui(processed, origin):
            if (processed, line) in extracted_set: continue
            
            ctx = "\n".join(lines[max(0, line-2):min(len(lines), line+1)])
            masked, is_m = _mask_sensitive_data(processed, p_level)
            if is_m: privacy_hits += 1
            results.append(ExtractedString(text=masked, line=line, context=ctx, is_masked=is_m))
            extracted_set.add((processed, line))

    glossary = await load_project_glossary()
    glossary_ctx = {r.text: glossary[r.text] for r in results if r.text in glossary}
    
    return ExtractOutput(results=results, is_cached=False, telemetry=TelemetryData(duration_ms=(time.perf_counter()-start_ts)*1000, files_processed=1, keys_extracted=len(results), privacy_shield_hits=privacy_hits), glossary_context=glossary_ctx)

# ----------------- 后续辅助逻辑 -----------------

def _validate_safe_path(path: str) -> str:
    ws_root = os.path.normpath(os.path.abspath(WORKSPACE_ROOT)).lower()
    target_path = os.path.normpath(os.path.abspath(os.path.join(WORKSPACE_ROOT, path)))
    if not target_path.lower().startswith(ws_root): raise PermissionError("Access Denied.")
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
    temp_file = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json")
    async with aiofiles.open(temp_file, mode='w', encoding='utf-8') as f:
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
    base_p, target_p = _validate_safe_path(os.path.join(target_dir, f"{base_lang}.json")), _validate_safe_path(os.path.join(target_dir, f"{lang_code}.json"))
    try:
        async with aiofiles.open(base_p, "r", encoding="utf-8") as f: b_d = json.loads(await f.read())
        async with aiofiles.open(target_p, "r", encoding="utf-8") as f: t_d = json.loads(await f.read())
    except: return {}
    return {k: v for k, v in b_d.items() if k not in t_d}
