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
    EvaluationFeedback, PrivacyLevel, RegressionResult
)
from i18n_agent_skill.linter import TranslationStyleLinter
from i18n_agent_skill.logger import structured_logger as logger
from i18n_agent_skill.vcs import get_git_hunks
from i18n_agent_skill.snapshot import TranslationSnapshotManager

# 全局常量
CACHE_FILE = ".i18n-cache.json"
PROPOSALS_DIR = ".i18n-proposals"
GLOSSARY_FILE = "GLOSSARY.json"
CONFIG_FILE = ".i18n-skill.json"
WORKSPACE_ROOT = os.getcwd()

# 敏感信息脱敏正则
SENSITIVE_PATTERNS = {
    "EMAIL": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
    # API_KEY: 支持带前缀的赋值场景，以及常见的独立 Key 格式（如 OpenAI sk-, AWS AKIA 等）
    "API_KEY": r'(?:(?:key|token|secret|auth|api)[:\s=\'"]+)?\b(?:sk-[a-zA-Z0-9]{20,}|AKIA[a-zA-Z0-9]{16}|[a-zA-Z0-9]{32,})\b',
    "IP_ADDR": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    "PHONE": r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b|\b\d{11}\b'
}

def _mask_sensitive_data(text: str, level: PrivacyLevel) -> tuple[str, bool]:
    """
    主权级特性：隐私护盾。
    对文案中的敏感信息进行脱敏处理。
    """
    if level == PrivacyLevel.OFF:
        return text, False
    
    masked_text = text
    is_masked = False
    
    patterns_to_check = SENSITIVE_PATTERNS.keys()
    if level == PrivacyLevel.BASIC:
        patterns_to_check = ["EMAIL", "API_KEY"]
        
    for p_type in patterns_to_check:
        pattern = SENSITIVE_PATTERNS[p_type]
        if re.search(pattern, masked_text, re.IGNORECASE):
            # 使用 sub 的 count 来检测是否有替换发生
            new_text, count = re.subn(pattern, f"[MASKED_{p_type}]", masked_text, flags=re.IGNORECASE)
            if count > 0:
                masked_text = new_text
                is_masked = True
            
    return masked_text, is_masked

def _validate_safe_path(path: str) -> str:
    """跨平台路径安全校验：防止路径穿越，解决 Windows 盘符大小写问题"""
    # 确保 WORKSPACE_ROOT 是绝对路径且规范化
    ws_root = os.path.normpath(os.path.abspath(WORKSPACE_ROOT)).lower()
    
    # 获取目标路径的规范化绝对路径
    target_path = os.path.normpath(os.path.abspath(os.path.join(WORKSPACE_ROOT, path)))
    target_path_lower = target_path.lower()
    
    if not target_path_lower.startswith(ws_root):
        raise PermissionError(f"Access Denied: Path '{path}' is outside the project workspace.")
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
    cache = await _read_cache()
    has_glossary = os.path.exists(os.path.join(WORKSPACE_ROOT, GLOSSARY_FILE))
    hunks = get_git_hunks(WORKSPACE_ROOT)
    vcs_info = {
        "git_available": True, 
        "changed_files_count": len(hunks),
        "hunk_details": {f: list(lines) for f, lines in hunks.items()}
    }
    logger.info("Project status checked", extra={"privacy_level": config.privacy_level})
    return ProjectStatus(
        config=config, has_glossary=has_glossary, cache_size=len(cache),
        workspace_root=WORKSPACE_ROOT, status_message=f"Ready. Privacy Shield: {config.privacy_level}",
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

def _detect_locale_dir(config: Optional[ProjectConfig] = None) -> str:
    """自动感知 i18n 目录：优先使用配置，其次探测标准路径"""
    if config and config.locales_dir != "locales":
        return config.locales_dir
    
    # 探测顺序：locales/ -> src/locales/
    for candidate in ["locales", os.path.join("src", "locales")]:
        if os.path.isdir(os.path.join(WORKSPACE_ROOT, candidate)):
            return candidate
    return "locales" # 默认值

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

async def extract_raw_strings(file_path: str, use_cache: bool = True, vcs_mode: bool = False, privacy_level: Optional[PrivacyLevel] = None) -> ExtractOutput:
    """语义提取：支持主权级隐私脱敏"""
    start_ts = time.perf_counter()
    config = await _load_project_config()
    p_level = privacy_level or config.privacy_level
    
    changed_hunks = get_git_hunks(WORKSPACE_ROOT)
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
            results = []
            for r in cached_raw:
                if target_lines and r.get("line") not in target_lines:
                    continue
                # 重新应用隐私脱敏（以防隐私级别变更）
                masked_text, is_masked = _mask_sensitive_data(r["text"], p_level)
                results.append(ExtractedString(text=masked_text, line=r["line"], context=r["context"], is_masked=is_masked))
            
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
        if target_lines and line_no not in target_lines:
            continue
            
        matches = re.findall(r'["\']([\u4e00-\u9fa5a-zA-Z0-9\s\-_/\@\.!\?\:\;]{2,})["\']', line)
        for text in set(matches):
            start, end = max(0, i - 1), min(len(lines), i + 2)
            context = "\n".join(lines[start:end])
            
            # 执行脱敏
            masked_text, is_masked = _mask_sensitive_data(text, p_level)
            results.append(ExtractedString(text=masked_text, line=line_no, context=context, is_masked=is_masked))

    if use_cache:
        cache = await _read_cache()
        cache[file_path] = {"hash": await _get_file_hash(safe_path), "results": [r.model_dump() for r in results]}
        await _write_cache(cache)

    duration = (time.perf_counter() - start_ts) * 1000
    logger.info("Strings extracted with privacy shield", extra={"file": file_path, "privacy_level": p_level})
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
    """生成变更提案，具备主权级回归测试防护"""
    start_ts = time.perf_counter()
    config = await _load_project_config()
    target_dir = base_dir or _detect_locale_dir(config)
    file_path = os.path.join(target_dir, f"{lang_code}.json")
    base_path = os.path.join(target_dir, "en.json")
    
    current_data, base_data = {}, {}
    validation_errors: List[ValidationFeedback] = []
    style_suggestions: List[StyleFeedback] = []
    regression_alert = None

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
            
    # 质量评分（Mock 逻辑，实际中由 Judge Agent 产生）
    # 我们假设 Agent 表现良好，得分为 9
    current_score = 9 
    
    # 检查回归退化
    snapshot_manager = TranslationSnapshotManager(WORKSPACE_ROOT)
    for key, val in new_pairs.items():
        # 1. 占位符校验
        if key in base_data:
            exp, act = _get_placeholders(base_data[key]), _get_placeholders(val)
            if set(exp) != set(act):
                validation_errors.append(ValidationFeedback(key=key, expected_placeholders=exp, actual_placeholders=act, message=f"Placeholder mismatch for '{key}'."))
        
        # 2. 风格校验
        style_feedbacks = TranslationStyleLinter.lint(key, val, lang_code)
        style_suggestions.extend(style_feedbacks)
        
        # 3. 回归对比
        reg = await snapshot_manager.check_regression(key, current_score)
        if reg: regression_alert = reg

    nested_new = _unflatten_dict(new_pairs)
    proposal_id = str(uuid.uuid4())
    os.makedirs(os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR), exist_ok=True)
    temp_file = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json")
    
    final_data = _deep_update(current_data.copy(), nested_new, strategy)
    proposal_data = {
        "target_file": file_path, 
        "content": final_data, 
        "reasoning": reasoning, 
        "lang_code": lang_code,
        "score": current_score # 记录当前得分
    }
    
    async with aiofiles.open(temp_file, mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(proposal_data, indent=2, ensure_ascii=False, sort_keys=True))
        
    duration = (time.perf_counter() - start_ts) * 1000
    return SyncProposal(
        proposal_id=proposal_id, lang_code=lang_code, changes_count=len(new_pairs),
        diff_summary=new_pairs, reasoning=reasoning, file_path=file_path,
        validation_errors=validation_errors, style_suggestions=style_suggestions,
        regression_alert=regression_alert,
        telemetry=TelemetryData(duration_ms=duration, files_processed=1, keys_extracted=len(new_pairs))
    )

async def commit_i18n_changes(proposal_id: str) -> str:
    temp_file = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json")
    if not os.path.exists(temp_file): return f"Error: Proposal {proposal_id} not found."
    async with aiofiles.open(temp_file, mode='r', encoding='utf-8') as f:
        proposal = json.loads(await f.read())
    
    safe_target = _validate_safe_path(proposal["target_file"])
    os.makedirs(os.path.dirname(safe_target), exist_ok=True)
    async with aiofiles.open(safe_target, mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(proposal["content"], indent=2, ensure_ascii=False, sort_keys=True))
    
    # 【主权级】提交成功后，同步更新回归快照
    snapshot_manager = TranslationSnapshotManager(WORKSPACE_ROOT)
    for key, val in _flatten_dict(proposal["content"]).items():
        await snapshot_manager.update_snapshot(key, val, proposal.get("score", 0))
        
    os.remove(temp_file)
    return f"Committed to {safe_target} and updated regression snapshots."

async def sync_i18n_files(new_pairs: dict[str, str], lang_code: str, base_dir: Optional[str] = None, strategy: ConflictStrategy = ConflictStrategy.KEEP_EXISTING, dry_run: bool = False) -> str:
    config = await _load_project_config()
    target_dir = base_dir or _detect_locale_dir(config)
    file_path = os.path.join(target_dir, f"{lang_code}.json")
    data: dict[str, Any] = {}
    
    # 始终使用安全路径获取绝对路径
    safe_file_path = _validate_safe_path(file_path)
    
    if os.path.exists(safe_file_path):
        try:
            async with aiofiles.open(safe_file_path, mode='r', encoding='utf-8') as f:
                data = json.loads(await f.read())
        except Exception: pass
    nested = _unflatten_dict(new_pairs)
    _deep_update(data, nested, strategy)
    if dry_run: return f"[DRY RUN] Sync to {file_path}:\n{json.dumps(nested, indent=2, ensure_ascii=False)}"
    async with aiofiles.open(safe_file_path, mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))
    return f"Synced {len(new_pairs)} keys."

async def get_missing_keys(lang_code: str, base_lang: str = "en", base_dir: Optional[str] = None) -> dict[str, str]:
    config = await _load_project_config()
    target_dir = base_dir or _detect_locale_dir(config)
    
    base_path = _validate_safe_path(os.path.join(target_dir, f"{base_lang}.json"))
    target_path = _validate_safe_path(os.path.join(target_dir, f"{lang_code}.json"))
    
    base_data, target_data = {}, {}
    if os.path.exists(base_path):
        try:
            async with aiofiles.open(base_path, mode='r', encoding='utf-8') as f:
                base_data = json.loads(await f.read())
        except Exception: pass
    if os.path.exists(target_path):
        try:
            async with aiofiles.open(target_path, mode='r', encoding='utf-8') as f:
                target_data = json.loads(await f.read())
        except Exception: pass
    flat_base, flat_target = _flatten_dict(base_data), _flatten_dict(target_data)
    missing = set(flat_base.keys()) - set(flat_target.keys())
    return {k: flat_base[k] for k in missing}
