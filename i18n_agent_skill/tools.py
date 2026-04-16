import hashlib
import json
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

import aiofiles

# 延迟导入 Tree-sitter 以支持自愈提示
try:
    import tree_sitter_javascript as ts_js
    import tree_sitter_typescript as ts_ts
    from tree_sitter_languages import get_language, get_parser
    from tree_sitter import Language, Parser
    DEPENDENCIES_INSTALLED = True
except ImportError:
    DEPENDENCIES_INSTALLED = False

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

# 初始化语言包
if DEPENDENCIES_INSTALLED:
    try:
        LANGUAGES = {
            "javascript": Language(ts_js.language()),
            "tsx": Language(ts_ts.language_tsx()),
            "vue": get_language("vue")
        }
    except Exception:
        # Fallback to js if vue specific is not loaded
        LANGUAGES = {
            "javascript": Language(ts_js.language()),
            "tsx": Language(ts_ts.language_tsx()),
            "vue": Language(ts_js.language())
        }
else:
    LANGUAGES = {}

# [v1.2.2] 优化查询定义
QUERY_STRINGS = {
    "js": """
        (string) @string_literal
        (template_string) @template_string
    """,
    "jsx": """
        (string) @string_literal
        (template_string) @template_string
        (jsx_text) @jsx_text
        (jsx_attribute 
            (property_identifier) @prop_name
            (#match? @prop_name "^(placeholder|title|label|alt|aria-label)$")
            (string) @ui_attr_value
        )
    """,
    "vue": """
        (text) @vue_text
        (attribute 
            (attribute_name) @attr_name
            (#match? @attr_name "^(placeholder|title|label|alt)$")
            (quoted_attribute_value) @ui_attr_value
        )
        (script_element (raw_text) @script_content)
    """
}

class TreeSitterScanner:
    """
    [v1.2.2 强化版] 
    使用 tree-sitter-languages 兼容性加载器。
    """
    def __init__(self, content: str, file_ext: str):
        self.content_str = content
        self.content_bytes = content.encode('utf-8')
        self.file_ext = file_ext
        self.parser = Parser()

    def _map_lang(self, ext: str) -> Tuple[str, str]:
        if ext in (".js", ".jsx"): return "javascript", "jsx"
        if ext in (".ts", ".tsx"): return "tsx", "jsx"
        if ext == ".vue": return "vue", "vue"
        return "javascript", "js"

    def scan(self, target_content: Optional[bytes] = None, target_ext: Optional[str] = None) -> List[Tuple[str, int, str]]:
        if not DEPENDENCIES_INSTALLED: return []
        
        current_content = target_content or self.content_bytes
        current_ext = target_ext or self.file_ext
        lang_key, query_key = self._map_lang(current_ext)
        
        if lang_key not in LANGUAGES: return []
        
        self.parser.set_language(LANGUAGES[lang_key])
        tree = self.parser.parse(current_content)
        query = LANGUAGES[lang_key].query(QUERY_STRINGS.get(query_key, QUERY_STRINGS["js"]))
        captures = query.captures(tree.root_node)
        
        results = []
        for node, capture_name in captures:
            if capture_name in ("prop_name", "attr_name"): continue
            
            if capture_name == "script_content":
                results.extend(self.scan(node.text, ".js"))
                continue

            text = node.text.decode('utf-8').strip('"\'`')
            if not text or text.isspace(): continue
            
            line_no = node.start_point[0] + 1
            origin = "text_node" if capture_name in ("jsx_text", "vue_text") else "code"
            if capture_name == "ui_attr_value": origin = "ui_attr"
            
            results.append((text, line_no, origin))
        return results

def _is_natural_language(text: str, origin: str) -> bool:
    t = text.strip()
    if not t or len(t) < 2: return False
    if re.search(r'[^\x00-\x7f]', t):
        return bool(re.search(r'[\w\u4e00-\u9fa5\u3040-\u30ff]', t))
    if origin in ("text_node", "ui_attr"):
        if re.match(r'^[0-9\s.,:\-_]+$', t): return False
        if re.match(r'^[a-z0-9\-]+$', t) and "-" in t: return False
        return True
    if " " in t or re.search(r'[.!?:]$', t): return True
    if t[0].isupper() and not t.isupper() and len(t) > 2: return True
    return False

async def extract_raw_strings(file_path: str, use_cache: bool = True, vcs_mode: bool = False, privacy_level: Optional[PrivacyLevel] = None) -> ExtractOutput:
    if not DEPENDENCIES_INSTALLED:
        return ExtractOutput(error=ErrorInfo(
            error_code="DEP_MISSING",
            message="Tree-sitter dependencies not found.",
            suggested_action="Please run: pip install -e .",
            executable_hint="pip install -e ."
        ))

    start_ts = time.perf_counter()
    config = await _load_project_config()
    p_level = privacy_level or config.privacy_level
    privacy_hits, results = 0, []

    try:
        safe_p = _validate_safe_path(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        async with aiofiles.open(safe_p, mode='r', encoding='utf-8') as f:
            content = await f.read()
    except Exception as e:
        return ExtractOutput(error=ErrorInfo(error_code="IO_ERR", message=str(e)))

    scanner = TreeSitterScanner(content, ext)
    all_lines = content.splitlines()
    extracted_set = set()

    for text, line, origin in scanner.scan():
        processed = re.sub(r'\$\{(.*?)\}', r'{\1}', text)
        if _is_natural_language(processed, origin):
            if (processed, line) in extracted_set: continue
            ctx = "\n".join(all_lines[max(0, line-2):min(len(all_lines), line+1)])
            masked, is_m = _mask_sensitive_data(processed, p_level)
            if is_m: privacy_hits += 1
            results.append(ExtractedString(text=masked, line=line, context=ctx, is_masked=is_m))
            extracted_set.add((processed, line))

    glossary = await load_project_glossary()
    glossary_ctx = {r.text: glossary[r.text] for r in results if r.text in glossary}
    return ExtractOutput(results=results, is_cached=False, telemetry=TelemetryData(duration_ms=(time.perf_counter()-start_ts)*1000, files_processed=1, keys_extracted=len(results), privacy_shield_hits=privacy_hits), glossary_context=glossary_ctx)

# ----------------- 恢复缺失的 API 函数 -----------------

async def sync_i18n_files(new_pairs: dict[str, str], lang_code: str, base_dir: Optional[str] = None, strategy: ConflictStrategy = ConflictStrategy.KEEP_EXISTING) -> str:
    """[RESTORED] 快速同步函数，主要用于简单的一键写入。"""
    config = await _load_project_config()
    target_dir = base_dir or _detect_locale_dir(config)
    file_path = os.path.join(target_dir, f"{lang_code}.json")
    
    current_data = {}
    if os.path.exists(file_path):
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            current_data = json.loads(await f.read())
            
    final_data = _deep_update(current_data, _unflatten_dict(new_pairs), strategy)
    async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(final_data, indent=2, ensure_ascii=False, sort_keys=True))
    return f"Synced {len(new_pairs)} keys to {file_path}"

async def refine_i18n_proposal(proposal_id: str, feedback: str) -> str:
    """[RESTORED] 交互微调：Agent 根据用户反馈修改提案。"""
    temp_file = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json")
    if not os.path.exists(temp_file): return f"Error: Proposal {proposal_id} not found."
    async with aiofiles.open(temp_file, mode='r', encoding='utf-8') as f:
        data = json.loads(await f.read())
    data["feedback_history"] = data.get("feedback_history", [])
    data["feedback_history"].append(feedback)
    async with aiofiles.open(temp_file, mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False))
    return f"Feedback recorded for proposal {proposal_id}. Please adjust the plan."

# ----------------- 其他基础逻辑 -----------------

def _mask_sensitive_data(text: str, level: PrivacyLevel) -> tuple[str, bool]:
    if level == PrivacyLevel.OFF: return text, False
    masked_text, is_masked = text, False
    patterns = {"EMAIL": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', "API_KEY": r'\b(?:sk-[a-zA-Z0-9]{20,}|AKIA[a-zA-Z0-9]{16}|[a-zA-Z0-9]{32,})\b'}
    for p_type, pattern in patterns.items():
        if re.search(pattern, masked_text, re.IGNORECASE):
            masked_text, count = re.subn(pattern, f"[MASKED_{p_type}]", masked_text, flags=re.IGNORECASE)
            if count > 0: is_masked = True
    return masked_text, is_masked

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
    except: return ProjectConfig()

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
    for candidate in ["locales", "src/locales"]:
        if os.path.isdir(os.path.join(WORKSPACE_ROOT, candidate)): return candidate
    return "locales"

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
    safe_target = _validate_safe_path(data["target_file"])
    os.makedirs(os.path.dirname(safe_target), exist_ok=True)
    async with aiofiles.open(safe_target, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data["content"], indent=2, ensure_ascii=False, sort_keys=True))
    snapshot_mgr = TranslationSnapshotManager(WORKSPACE_ROOT)
    for k, v in _flatten_dict(data["content"]).items(): await snapshot_mgr.update_snapshot(k, v, 9)
    os.remove(temp_p)
    return f"Committed: {safe_target}."

async def get_missing_keys(lang_code: str, base_lang: str = "en", base_dir: Optional[str] = None) -> dict[str, str]:
    config = await _load_project_config()
    target_dir = base_dir or _detect_locale_dir(config)
    base_p, target_p = _validate_safe_path(os.path.join(target_dir, f"{base_lang}.json")), _validate_safe_path(os.path.join(target_dir, f"{lang_code}.json"))
    try:
        async with aiofiles.open(base_p, "r", encoding="utf-8") as f: b_d = json.loads(await f.read())
        async with aiofiles.open(target_p, "r", encoding="utf-8") as f: t_d = json.loads(await f.read())
    except: return {}
    return {k: v for k, v in b_d.items() if k not in t_d}

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
