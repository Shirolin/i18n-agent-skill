import json
import re
import os
import hashlib
import uuid
import aiofiles
import time
from typing import Any, Optional, Dict, List, Set

from i18n_agent_skill.models import (
    ConflictStrategy, ExtractedString, ExtractOutput, 
    ErrorInfo, SyncProposal, ValidationFeedback, 
    ProjectConfig, ProjectStatus, TelemetryData, StyleFeedback,
    EvaluationFeedback
)
from i18n_agent_skill.linter import TranslationStyleLinter
from i18n_agent_skill.logger import structured_logger as logger
from i18n_agent_skill.vcs import get_git_hunks

# 全局常量
CACHE_FILE = ".i18n-cache.json"
PROPOSALS_DIR = ".i18n-proposals"
GLOSSARY_FILE = "GLOSSARY.json"
CONFIG_FILE = ".i18n-skill.json"
WORKSPACE_ROOT = os.getcwd()

def _validate_safe_path(path: str) -> str:
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(WORKSPACE_ROOT):
        raise PermissionError(f"Access Denied: Path '{path}' is outside the project workspace.")
    return abs_path

async def _load_project_config() -> ProjectConfig:
    config_path = os.path.join(WORKSPACE_ROOT, CONFIG_FILE)
    if not os.path.exists(config_path): return ProjectConfig()
    try:
        async with aiofiles.open(config_path, "r", encoding="utf-8") as f:
            return ProjectConfig(**json.loads(await f.read()))
    except Exception: return ProjectConfig()

async def check_project_status() -> ProjectStatus:
    config = await _load_project_config()
    cache = await _read_cache()
    has_glossary = os.path.exists(os.path.join(WORKSPACE_ROOT, GLOSSARY_FILE))
    
    # 皇冠级：获取具体的变动行号（Hunks）
    hunks = get_git_hunks(WORKSPACE_ROOT)
    vcs_info = {
        "git_available": True, 
        "changed_files_count": len(hunks),
        "hunk_details": {f: list(lines) for f, lines in hunks.items()}
    }
    
    logger.info("Project status checked", extra={"changed_files": len(hunks)})
    return ProjectStatus(
        config=config, has_glossary=has_glossary, cache_size=len(cache),
        workspace_root=WORKSPACE_ROOT, status_message="Ready. Hunk-level VCS sensing active.",
        vcs_info=vcs_info
    )

async def load_project_glossary() -> Dict[str, str]:
    glossary_path = os.path.join(WORKSPACE_ROOT, GLOSSARY_FILE)
    if not os.path.exists(glossary_path): return {}
    try:
        async with aiofiles.open(glossary_path, "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    except Exception: return {}

async def update_project_glossary(term: str, translation: str) -> str:
    glossary_path = os.path.join(WORKSPACE_ROOT, GLOSSARY_FILE)
    glossary = await load_project_glossary()
    glossary[term] = translation
    async with aiofiles.open(glossary_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(glossary, indent=2, ensure_ascii=False, sort_keys=True))
    return f"Learned term: '{term}' -> '{translation}'"

def _get_placeholders(text: str) -> List[str]:
    pattern = r'\{\{.*?\}\}|\{.*?\}'
    return re.findall(pattern, text)

async def _get_file_hash(file_path: str) -> str:
    safe_path = _validate_safe_path(file_path)
    hash_md5 = hashlib.md5()
    async with aiofiles.open(safe_path, "rb") as f:
        while chunk := await f.read(4096):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

async def _read_cache() -> Dict[str, Any]:
    cache_path = os.path.join(WORKSPACE_ROOT, CACHE_FILE)
    if not os.path.exists(cache_path): return {}
    try:
        async with aiofiles.open(cache_path, "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    except Exception: return {}

async def _write_cache(cache: Dict[str, Any]) -> None:
    cache_path = os.path.join(WORKSPACE_ROOT, CACHE_FILE)
    async with aiofiles.open(cache_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(cache, indent=2, ensure_ascii=False))

async def extract_raw_strings(file_path: str, use_cache: bool = True, vcs_mode: bool = False) -> ExtractOutput:
    """语义提取：支持 PR 级 Hunk 精准防护"""
    start_ts = time.perf_counter()
    
    # 皇冠级：Hunk 级增量防护
    changed_hunks = get_git_hunks(WORKSPACE_ROOT)
    # 如果开启 VCS 模式且文件未变动，直接跳过
    if vcs_mode and file_path not in changed_hunks:
        return ExtractOutput(results=[], is_cached=True)

    target_lines = changed_hunks.get(file_path) if vcs_mode else None

    try:
        safe_path = _validate_safe_path(file_path)
    except PermissionError as e:
        return ExtractOutput(error=ErrorInfo(error_code="PATH_OUT_OF_WORKSPACE", message=str(e), suggested_action="..."))

    if use_cache:
        file_hash = await _get_file_hash(safe_path)
        cache = await _read_cache()
        if file_path in cache and cache[file_path].get("hash") == file_hash:
            duration = (time.perf_counter() - start_ts) * 1000
            cached_raw = cache[file_path].get("results", [])
            # 如果是 Hunk 模式，从全量缓存中再次过滤符合行号的结果
            if target_lines:
                results = [ExtractedString(**r) for r in cached_raw if r.get("line") in target_lines]
            else:
                results = [ExtractedString(**r) for r in cached_raw]
            
            return ExtractOutput(results=results, is_cached=True, telemetry=TelemetryData(duration_ms=duration, files_processed=1, cache_hits=1, keys_extracted=len(results)))

    try:
        async with aiofiles.open(safe_path, mode='r', encoding='utf-8') as f:
            content = await f.read()
            lines = content.splitlines()
    except Exception as e:
        return ExtractOutput(error=ErrorInfo(error_code="READ_ERROR", message=str(e), suggested_action="..."))

    results = []
    for i, line in enumerate(lines):
        line_no = i + 1
        # 皇冠级：如果行号不在 Hunk 区间内，跳过（除非非 VCS 模式）
        if target_lines and line_no not in target_lines:
            continue
            
        matches = re.findall(r'["\']([\u4e00-\u9fa5a-zA-Z0-9\s\,\.\!\?\:\;]{2,})["\']', line)
        for text in set(matches):
            start, end = max(0, i - 1), min(len(lines), i + 2)
            results.append(ExtractedString(text=text, line=line_no, context="\n".join(lines[start:end])))

    if use_cache:
        cache = await _read_cache()
        cache[file_path] = {"hash": await _get_file_hash(safe_path), "results": [r.model_dump() for r in results]}
        await _write_cache(cache)

    duration = (time.perf_counter() - start_ts) * 1000
    logger.info("Strings extracted", extra={"file": file_path, "keys": len(results), "duration_ms": duration})
    return ExtractOutput(results=results, is_cached=False, telemetry=TelemetryData(duration_ms=duration, files_processed=1, cache_hits=0, keys_extracted=len(results)))

def _flatten_dict(d: dict[str, Any], parent_key: str = '', sep: str = '.') -> dict[str, str]:
    items: list[tuple[str, str]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict): items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else: items.append((new_key, str(v)))
    return dict(items)

def _unflatten_dict(d: dict[str, Any], sep: str = '.') -> dict[str, Any]:
    result: dict[str, Any] = {}
    for k, v in d.items():
        parts = k.split(sep)
        d_ref = result
        for part in parts[:-1]:
            if part not in d_ref: d_ref[part] = {}
            d_ref = d_ref[part]
        d_ref[parts[-1]] = v
    return result

def _deep_update(d: dict[str, Any], u: dict[str, Any], strategy: ConflictStrategy = ConflictStrategy.KEEP_EXISTING) -> dict[str, Any]:
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict): _deep_update(d[k], v, strategy)
        else:
            if k in d and strategy == ConflictStrategy.KEEP_EXISTING: continue
            d[k] = v
    return d

async def propose_sync_i18n(
    new_pairs: dict[str, str], 
    lang_code: str, 
    reasoning: str,
    base_dir: Optional[str] = None, 
    strategy: ConflictStrategy = ConflictStrategy.KEEP_EXISTING
) -> SyncProposal:
    """生成变更提案，具备 LLM-as-a-Judge 自动评审插槽"""
    start_ts = time.perf_counter()
    config = await _load_project_config()
    target_dir = base_dir or _detect_locale_dir(config)
    file_path = os.path.join(target_dir, f"{lang_code}.json")
    base_path = os.path.join(target_dir, "en.json")
    
    current_data, base_data = {}, {}
    validation_errors: List[ValidationFeedback] = []
    style_suggestions: List[StyleFeedback] = []

    if os.path.exists(base_path):
        try:
            async with aiofiles.open(base_path, mode='r', encoding='utf-8') as f:
                base_data = _flatten_dict(json.loads(await f.read()))
        except Exception: pass

    if os.path.exists(file_path):
        try:
            async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
                current_data = json.loads(await f.read())
        except Exception: pass
            
    for key, val in new_pairs.items():
        if key in base_data:
            exp, act = _get_placeholders(base_data[key]), _get_placeholders(val)
            if set(exp) != set(act):
                validation_errors.append(ValidationFeedback(key=key, expected_placeholders=exp, actual_placeholders=act, message=f"Placeholder mismatch for '{key}'."))
        
        style_feedbacks = TranslationStyleLinter.lint(key, val, lang_code)
        style_suggestions.extend(style_feedbacks)

    # 皇冠级：评审插槽 (Mock LLM-as-a-Judge)
    # 实际应用中此处可发起第二次 LLM 调用
    logger.info("Translation review started", extra={"proposal_keys": len(new_pairs)})

    nested_new = _unflatten_dict(new_pairs)
    proposal_id = str(uuid.uuid4())
    os.makedirs(os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR), exist_ok=True)
    temp_file = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json")
    
    final_data = _deep_update(current_data.copy(), nested_new, strategy)
    proposal_data = {"target_file": file_path, "content": final_data, "reasoning": reasoning, "lang_code": lang_code}
    
    async with aiofiles.open(temp_file, mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(proposal_data, indent=2, ensure_ascii=False, sort_keys=True))
        
    duration = (time.perf_counter() - start_ts) * 1000
    return SyncProposal(
        proposal_id=proposal_id, lang_code=lang_code, changes_count=len(new_pairs),
        diff_summary=new_pairs, reasoning=reasoning, file_path=file_path,
        validation_errors=validation_errors, style_suggestions=style_suggestions,
        telemetry=TelemetryData(duration_ms=duration, files_processed=1, keys_extracted=len(new_pairs))
    )

def _detect_locale_dir(config: Optional[ProjectConfig] = None) -> str:
    if config and config.locales_dir != "locales": return config.locales_dir
    candidates = ["locales", "src/locales", "i18n", "src/assets/locales"]
    for candidate in candidates:
        if os.path.isdir(os.path.join(WORKSPACE_ROOT, candidate)): return candidate
    return "locales"

async def commit_i18n_changes(proposal_id: str) -> str:
    temp_file = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json")
    if not os.path.exists(temp_file): return f"Error: Proposal {proposal_id} not found."
    async with aiofiles.open(temp_file, mode='r', encoding='utf-8') as f:
        proposal = json.loads(await f.read())
    safe_target = _validate_safe_path(proposal["target_file"])
    os.makedirs(os.path.dirname(safe_target), exist_ok=True)
    async with aiofiles.open(safe_target, mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(proposal["content"], indent=2, ensure_ascii=False, sort_keys=True))
    os.remove(temp_file)
    return f"Committed to {safe_target}"

async def refine_i18n_proposal(proposal_id: str, feedback: str) -> SyncProposal:
    temp_file = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json")
    if not os.path.exists(temp_file): raise FileNotFoundError(f"Proposal {proposal_id} not found.")
    async with aiofiles.open(temp_file, mode='r', encoding='utf-8') as f:
        raw = json.loads(await f.read())
    return SyncProposal(
        proposal_id=proposal_id, lang_code=raw["lang_code"], changes_count=0,
        diff_summary={}, reasoning=f"Refined based on feedback: {feedback}",
        file_path=raw["target_file"]
    )

async def sync_i18n_files(new_pairs: dict[str, str], lang_code: str, base_dir: Optional[str] = None, strategy: ConflictStrategy = ConflictStrategy.KEEP_EXISTING, dry_run: bool = False) -> str:
    config = await _load_project_config()
    target_dir = base_dir or _detect_locale_dir(config)
    file_path = os.path.join(target_dir, f"{lang_code}.json")
    data: dict[str, Any] = {}
    if os.path.exists(file_path):
        try:
            async with aiofiles.open(_validate_safe_path(file_path), mode='r', encoding='utf-8') as f:
                data = json.loads(await f.read())
        except Exception: pass
    nested = _unflatten_dict(new_pairs)
    _deep_update(data, nested, strategy)
    if dry_run: return f"[DRY RUN] Sync to {file_path}:\n{json.dumps(nested, indent=2, ensure_ascii=False)}"
    async with aiofiles.open(_validate_safe_path(file_path), mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))
    return f"Synced {len(new_pairs)} keys."

async def get_missing_keys(lang_code: str, base_lang: str = "en", base_dir: Optional[str] = None) -> dict[str, str]:
    config = await _load_project_config()
    target_dir = base_dir or _detect_locale_dir(config)
    base_file, target_file = os.path.join(target_dir, f"{base_lang}.json"), os.path.join(target_dir, f"{lang_code}.json")
    base_data, target_data = {}, {}
    if os.path.exists(base_file):
        try:
            async with aiofiles.open(_validate_safe_path(base_file), mode='r', encoding='utf-8') as f:
                base_data = json.loads(await f.read())
        except Exception: pass
    if os.path.exists(target_file):
        try:
            async with aiofiles.open(_validate_safe_path(target_file), mode='r', encoding='utf-8') as f:
                target_data = json.loads(await f.read())
        except Exception: pass
    flat_base, flat_target = _flatten_dict(base_data), _flatten_dict(target_data)
    missing = set(flat_base.keys()) - set(flat_target.keys())
    return {k: flat_base[k] for k in missing}
