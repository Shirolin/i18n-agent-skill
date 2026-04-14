import json
import re
import os
import logging
import hashlib
import uuid
import aiofiles
from typing import Any, Optional, Dict, List, Set
from i18n_agent_skill.models import (
    ConflictStrategy, ExtractedString, ExtractOutput, 
    ErrorInfo, SyncProposal, ValidationFeedback, 
    ProjectConfig, ProjectStatus
)

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# 全局常量
CACHE_FILE = ".i18n-cache.json"
PROPOSALS_DIR = ".i18n-proposals"
GLOSSARY_FILE = "GLOSSARY.json"
CONFIG_FILE = ".i18n-skill.json"
WORKSPACE_ROOT = os.getcwd()

def _validate_safe_path(path: str) -> str:
    """路径沙箱校验"""
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(WORKSPACE_ROOT):
        raise PermissionError(f"Access Denied: Path '{path}' is outside the project workspace.")
    return abs_path

async def _load_project_config() -> ProjectConfig:
    """加载 .i18n-skill.json 配置文件，若无则返回默认值"""
    config_path = os.path.join(WORKSPACE_ROOT, CONFIG_FILE)
    if not os.path.exists(config_path):
        return ProjectConfig()
    try:
        async with aiofiles.open(config_path, "r", encoding="utf-8") as f:
            content = await f.read()
            return ProjectConfig(**json.loads(content))
    except Exception as e:
        logger.warning(f"Failed to load config: {str(e)}. Using defaults.")
        return ProjectConfig()

async def check_project_status() -> ProjectStatus:
    """
    预检工具：大师级范式的开工自检。
    帮助 Agent 快速了解项目结构、配置契约及缓存状态。
    """
    config = await _load_project_config()
    cache = await _read_cache()
    has_glossary = os.path.exists(os.path.join(WORKSPACE_ROOT, GLOSSARY_FILE))
    
    status_msg = "项目就绪。请优先遵守配置契约中的 source_dirs 设定进行扫描。"
    if not has_glossary:
        status_msg += " 注意：未检测到术语表，翻译可能缺乏一致性背景。"
        
    return ProjectStatus(
        config=config,
        has_glossary=has_glossary,
        cache_size=len(cache),
        workspace_root=WORKSPACE_ROOT,
        status_message=status_msg
    )

def _detect_locale_dir(config: Optional[ProjectConfig] = None) -> str:
    """识别 i18n 目录，优先使用配置"""
    if config and config.locales_dir != "locales":
        return config.locales_dir
        
    candidates = ["locales", "src/locales", "i18n", "src/assets/locales"]
    for candidate in candidates:
        full_path = os.path.join(WORKSPACE_ROOT, candidate)
        if os.path.isdir(full_path):
            return candidate
    return "locales"

async def load_project_glossary() -> Dict[str, str]:
    """加载术语表"""
    glossary_path = os.path.join(WORKSPACE_ROOT, GLOSSARY_FILE)
    if not os.path.exists(glossary_path):
        return {}
    try:
        async with aiofiles.open(glossary_path, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)
    except Exception as e:
        logger.warning(f"Failed to load glossary: {str(e)}")
        return {}

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
    if not os.path.exists(cache_path):
        return {}
    try:
        async with aiofiles.open(cache_path, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)
    except Exception:
        return {}

async def _write_cache(cache: Dict[str, Any]) -> None:
    cache_path = os.path.join(WORKSPACE_ROOT, CACHE_FILE)
    async with aiofiles.open(cache_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(cache, indent=2, ensure_ascii=False))

async def extract_raw_strings(file_path: str, use_cache: bool = True) -> ExtractOutput:
    """语义提取工具：带沙箱校验、增量扫描与配置感知"""
    config = await _load_project_config()
    
    # 路径策略检查：如果是忽略目录，则跳过
    for ignore in config.ignore_dirs:
        if ignore in file_path:
            return ExtractOutput(error=ErrorInfo(
                error_code="IGNORE_PATH_SKIP",
                message=f"Path '{file_path}' is in the ignore list.",
                suggested_action="Skipping as per project policy."
            ))

    try:
        safe_path = _validate_safe_path(file_path)
    except PermissionError as e:
        return ExtractOutput(error=ErrorInfo(
            error_code="PATH_OUT_OF_WORKSPACE",
            message=str(e),
            suggested_action="Ensure the file path is within the project root."
        ))

    if not os.path.exists(safe_path):
        return ExtractOutput(error=ErrorInfo(
            error_code="FILE_NOT_FOUND",
            message=f"File not found: {file_path}",
            suggested_action="Check the path and try again."
        ))

    if use_cache:
        file_hash = await _get_file_hash(safe_path)
        cache = await _read_cache()
        if file_path in cache and cache[file_path].get("hash") == file_hash:
            cached_results = [ExtractedString(**r) for r in cache[file_path].get("results", [])]
            return ExtractOutput(results=cached_results, is_cached=True)

    try:
        async with aiofiles.open(safe_path, mode='r', encoding='utf-8') as f:
            content = await f.read()
            lines = content.splitlines()
    except (UnicodeDecodeError, Exception) as e:
        return ExtractOutput(error=ErrorInfo(
            error_code="BINARY_FILE_SKIP",
            message=f"Cannot decode {file_path} as UTF-8.",
            suggested_action="This file might be binary. Please scan text files."
        ))

    results = []
    for i, line in enumerate(lines):
        matches = re.findall(r'["\']([\u4e00-\u9fa5a-zA-Z0-9\s\,\.\!\?\:\;]{2,})["\']', line)
        for text in set(matches):
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            context = "\n".join(lines[start:end])
            results.append(ExtractedString(text=text, line=i + 1, context=context))

    if use_cache:
        cache = await _read_cache()
        cache[file_path] = {
            "hash": await _get_file_hash(safe_path),
            "results": [r.model_dump() for r in results]
        }
        await _write_cache(cache)

    return ExtractOutput(results=results, is_cached=False)

def _flatten_dict(d: dict[str, Any], parent_key: str = '', sep: str = '.') -> dict[str, str]:
    items: list[tuple[str, str]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, str(v)))
    return dict(items)

def _unflatten_dict(d: dict[str, Any], sep: str = '.') -> dict[str, Any]:
    result: dict[str, Any] = {}
    for k, v in d.items():
        parts = k.split(sep)
        d_ref = result
        for part in parts[:-1]:
            if part not in d_ref:
                d_ref[part] = {}
            d_ref = d_ref[part]
        d_ref[parts[-1]] = v
    return result

def _deep_update(d: dict[str, Any], u: dict[str, Any], strategy: ConflictStrategy = ConflictStrategy.KEEP_EXISTING) -> dict[str, Any]:
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            _deep_update(d[k], v, strategy)
        else:
            if k in d and strategy == ConflictStrategy.KEEP_EXISTING:
                continue
            d[k] = v
    return d

async def propose_sync_i18n(
    new_pairs: dict[str, str], 
    lang_code: str, 
    reasoning: str,
    base_dir: Optional[str] = None, 
    strategy: ConflictStrategy = ConflictStrategy.KEEP_EXISTING
) -> SyncProposal:
    """生成变更提案，具备自纠错反馈"""
    config = await _load_project_config()
    target_dir = base_dir or _detect_locale_dir(config)
    file_path = os.path.join(target_dir, f"{lang_code}.json")
    base_path = os.path.join(target_dir, "en.json")
    
    current_data = {}
    base_data = {}
    validation_errors = []

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
            
    for key, translated_val in new_pairs.items():
        if key in base_data:
            base_text = base_data[key]
            expected = _get_placeholders(base_text)
            actual = _get_placeholders(translated_val)
            if set(expected) != set(actual):
                validation_errors.append(ValidationFeedback(
                    key=key,
                    expected_placeholders=expected,
                    actual_placeholders=actual,
                    message=f"Key '{key}' 翻译后丢失或错误修改了占位符。预期: {expected}, 实际: {actual}。"
                ))

    nested_new = _unflatten_dict(new_pairs)
    proposal_id = str(uuid.uuid4())
    
    os.makedirs(os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR), exist_ok=True)
    temp_file = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json")
    
    final_data = _deep_update(current_data.copy(), nested_new, strategy)
    
    proposal_data = {
        "target_file": file_path,
        "content": final_data,
        "reasoning": reasoning
    }
    
    async with aiofiles.open(temp_file, mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(proposal_data, indent=2, ensure_ascii=False, sort_keys=True))
        
    return SyncProposal(
        proposal_id=proposal_id,
        lang_code=lang_code,
        changes_count=len(new_pairs),
        diff_summary=new_pairs,
        reasoning=reasoning,
        file_path=file_path,
        validation_errors=validation_errors
    )

async def commit_i18n_changes(proposal_id: str) -> str:
    """确认提交变更提案"""
    temp_file = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json")
    if not os.path.exists(temp_file):
        return f"Error: Proposal {proposal_id} not found."

    async with aiofiles.open(temp_file, mode='r', encoding='utf-8') as f:
        proposal = json.loads(await f.read())

    target_file = proposal["target_file"]
    content = proposal["content"]

    safe_target = _validate_safe_path(target_file)
    os.makedirs(os.path.dirname(safe_target), exist_ok=True)
    async with aiofiles.open(safe_target, mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(content, indent=2, ensure_ascii=False, sort_keys=True))
    
    os.remove(temp_file)
    return f"Successfully committed changes to {target_file}"

async def sync_i18n_files(
    new_pairs: dict[str, str], 
    lang_code: str, 
    base_dir: Optional[str] = None, 
    strategy: ConflictStrategy = ConflictStrategy.KEEP_EXISTING,
    dry_run: bool = False
) -> str:
    """传统同步逻辑"""
    config = await _load_project_config()
    target_dir = base_dir or _detect_locale_dir(config)
    file_path = os.path.join(target_dir, f"{lang_code}.json")
    
    data: dict[str, Any] = {}
    if os.path.exists(file_path):
        try:
            async with aiofiles.open(_validate_safe_path(file_path), mode='r', encoding='utf-8') as f:
                data = json.loads(await f.read())
        except Exception: pass
            
    nested_new_pairs = _unflatten_dict(new_pairs)
    _deep_update(data, nested_new_pairs, strategy)
    
    if dry_run:
        summary = json.dumps(nested_new_pairs, indent=2, ensure_ascii=False)
        return f"[DRY RUN] Sync to {file_path}:\n{summary}"

    async with aiofiles.open(_validate_safe_path(file_path), mode='w', encoding='utf-8') as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))
        
    return f"Synced {len(new_pairs)} keys to {file_path}"

async def get_missing_keys(lang_code: str, base_lang: str = "en", base_dir: Optional[str] = None) -> dict[str, str]:
    config = await _load_project_config()
    target_dir = base_dir or _detect_locale_dir(config)
    base_file = os.path.join(target_dir, f"{base_lang}.json")
    target_file = os.path.join(target_dir, f"{lang_code}.json")
    
    base_data = {}
    target_data = {}

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
            
    flat_base = _flatten_dict(base_data)
    flat_target = _flatten_dict(target_data)
            
    missing_keys = set(flat_base.keys()) - set(flat_target.keys())
    return {k: flat_base[k] for k in missing_keys}
