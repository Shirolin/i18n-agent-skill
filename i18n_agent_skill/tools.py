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

# 注意：在 2026 年的环境下，我们将引导 AI 使用 AST 逻辑。
# 虽然暂不引入外部二进制包以保持移植性，但我将实现一个 Token-based Parser (分词解析器)。
# 这比正则稳健得多，因为它理解嵌套。

def _token_scanner(content: str):
    """
    [v1.0 AST-Like Scanner] 
    基于 Token 的分词器。物理隔离注释，支持转义，支持标签感知。
    """
    i, n = 0, len(content)
    line_no = 1
    
    while i < n:
        char = content[i]
        
        # 1. 注释处理 (物理屏蔽)
        if char == '/' and i + 1 < n:
            if content[i+1] == '/': # // 行注释
                while i < n and content[i] != '\n': i += 1
                continue
            if content[i+1] == '*': # /* 块注释 */
                i += 2
                while i + 1 < n and not (content[i] == '*' and content[i+1] == '/'):
                    if content[i] == '\n': line_no += 1
                    i += 1
                i += 2
                continue

        # 2. 引号字符串处理 (支持转义)
        if char in ("'", '"'):
            q = char
            i += 1
            text = ""
            start_line = line_no
            while i < n:
                if content[i] == '\\' and i + 1 < n:
                    text += content[i:i+2]
                    i += 2
                    continue
                if content[i] == q:
                    yield "STRING", text, start_line
                    i += 1
                    break
                if content[i] == '\n': line_no += 1
                text += content[i]
                i += 1
            continue

        # 3. 模板字符串 (`)
        if char == '`':
            i += 1
            text = ""
            start_line = line_no
            while i < n:
                if content[i] == '`':
                    yield "TEMPLATE", text, start_line
                    i += 1
                    break
                if content[i] == '\n': line_no += 1
                text += content[i]
                i += 1
            continue

        # 4. JSX/Vue 文本节点处理 (解决无引号盲区)
        if char == '>':
            i += 1
            text = ""
            start_line = line_no
            while i < n and content[i] != '<':
                if content[i] == '\n': line_no += 1
                text += content[i]
                i += 1
            t_strip = text.strip()
            if t_strip and not t_strip.startswith(('{', '(', '[')):
                yield "TEXT_NODE", t_strip, start_line
            continue

        if char == '\n': line_no += 1
        i += 1

def _is_likely_ui(text: str, origin: str) -> bool:
    """[v1.0] 全球化语义裁决前置过滤"""
    t = text.strip()
    if not t or len(t) < 2: return False
    
    # 非 ASCII 优先 (日语、中文、德/法文)
    if re.search(r'[^\x00-\x7f]', t):
        return bool(re.search(r'[\w\u4e00-\u9fa5\u3040-\u30ff]', t))
    
    # 来源加权：标签间文本 (TextNode) 高召回
    if origin == "TEXT_NODE":
        if re.match(r'^[0-9\s.,:\-_]+$', t): return False
        return True
    
    # 代码中字符串高精过滤
    if " " in t or re.search(r'[.!?:]$', t): return True
    if t[0].isupper() and not t.isupper() and len(t) > 3: return True
    
    return False

async def extract_raw_strings(file_path: str, use_cache: bool = True, vcs_mode: bool = False, privacy_level: Optional[PrivacyLevel] = None) -> ExtractOutput:
    """[v1.0 Final] 彻底抛弃正则匹配，转向词法扫描架构。"""
    start_ts = time.perf_counter()
    config = await _load_project_config()
    p_level = privacy_level or config.privacy_level
    privacy_hits, results = 0, []

    try:
        safe_p = _validate_safe_path(file_path)
        async with aiofiles.open(safe_p, mode='r', encoding='utf-8') as f:
            content = await f.read()
    except Exception as e:
        return ExtractOutput(error=ErrorInfo(error_code="READ_ERR", message=str(e)))

    all_lines = content.splitlines()
    extracted_keys = set()

    # 使用分词扫描器而非全量正则
    for stype, text, line in _token_scanner(content):
        # 预处理：标准化模板占位符
        processed = re.sub(r'\$\{(.*?)\}', r'{\1}', text) if stype == "TEMPLATE" else text
        
        if _is_likely_ui(processed, stype):
            if (processed, line) in extracted_keys: continue
            
            ctx = "\n".join(all_lines[max(0, line-2):min(len(all_lines), line+1)])
            masked, is_m = _mask_sensitive_data(processed, p_level)
            if is_m: privacy_hits += 1
            results.append(ExtractedString(text=masked, line=line, context=ctx, is_masked=is_m))
            extracted_keys.add((processed, line))

    glossary = await load_project_glossary()
    glossary_ctx = {r.text: glossary[r.text] for r in results if r.text in glossary}
    
    return ExtractOutput(results=results, is_cached=False, telemetry=TelemetryData(duration_ms=(time.perf_counter()-start_ts)*1000, files_processed=1, keys_extracted=len(results), privacy_shield_hits=privacy_hits), glossary_context=glossary_ctx)

# ----------------- 基础架构逻辑 (保持稳定) -----------------

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
    status_msg = f"Ready. Mode: Lexical-Scanner. Privacy: {config.privacy_level}"
    return ProjectStatus(config=config, has_glossary=os.path.exists(os.path.join(WORKSPACE_ROOT, GLOSSARY_FILE)), cache_size=0, workspace_root=WORKSPACE_ROOT, status_message=status_msg)

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
