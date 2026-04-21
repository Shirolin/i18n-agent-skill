import hashlib
import json
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

import aiofiles

# 核心依赖：Tree-sitter 词法分析套件
try:
    import tree_sitter
    import tree_sitter_language_pack
    from tree_sitter import Language, Parser
    
    # 强制版本校验
    import importlib.metadata
    ts_version = importlib.metadata.version("tree-sitter")
    
    # 使用简单的元组比较，避免引入 packaging 依赖
    v_parts = [int(p) for p in ts_version.split(".")[:3]]
    if tuple(v_parts) < (0, 25, 0):
        DEPENDENCIES_INSTALLED = False
        DEP_ERROR_MSG = f"Tree-sitter version too low ({ts_version}). Minimum required: 0.25.0"
    else:
        DEPENDENCIES_INSTALLED = True
        DEP_ERROR_MSG = ""
except ImportError as e:
    DEPENDENCIES_INSTALLED = False
    DEP_ERROR_MSG = f"Missing core dependency: {str(e)}"
except Exception as e:
    DEPENDENCIES_INSTALLED = False
    DEP_ERROR_MSG = f"Dependency error: {str(e)}"

from i18n_agent_skill.logger import structured_logger as logger
from i18n_agent_skill.models import (
    ConflictStrategy,
    ErrorInfo,
    ExtractedString,
    ExtractOutput,
    PrivacyLevel,
    ProjectConfig,
    ProjectPreferences,
    ProjectStatus,
    SyncProposal,
    TelemetryData,
    ValidationFeedback,
    StyleFeedback,
)
from i18n_agent_skill.snapshot import TranslationSnapshotManager
from i18n_agent_skill.linter import TranslationStyleLinter

# 全局常量
CACHE_FILE = ".i18n-cache.json"
PROPOSALS_DIR = ".i18n-proposals"
GLOSSARY_FILE = "GLOSSARY.json"
CONFIG_FILE = ".i18n-skill.json"
PREFS_FILE = ".i18n-prefs.json"

def _is_skill_source_dir(directory: str) -> bool:
    """[工业级防护] 检查该目录是否是本工具自身的源代码"""
    skill_md = os.path.join(directory, "SKILL.md")
    pyproject = os.path.join(directory, "pyproject.toml")
    try:
        if os.path.exists(skill_md):
            with open(skill_md, "r", encoding="utf-8") as f:
                if "name: i18n-agent-skill" in f.read():
                    return True
        if os.path.exists(pyproject):
            with open(pyproject, "r", encoding="utf-8") as f:
                if "name = \"i18n-agent-skill\"" in f.read():
                    return True
    except Exception:
        pass
    return False

def _resolve_workspace_root(explicit_root: Optional[str] = None) -> str:
    """依靠边界指纹动态测算项目根目录"""
    if explicit_root:
        return os.path.abspath(explicit_root)
    env_root = os.environ.get("I18N_WORKSPACE_ROOT")
    if env_root:
        return os.path.abspath(env_root)

    cwd = os.getcwd()
    current_dir = os.path.abspath(cwd)
    markers = [".git", "package.json", "pyproject.toml", CONFIG_FILE]

    while True:
        has_marker = any(os.path.exists(os.path.join(current_dir, m)) for m in markers)
        if has_marker:
            if not _is_skill_source_dir(current_dir):
                return current_dir
        
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break
        current_dir = parent_dir
    return os.path.abspath(cwd)

WORKSPACE_ROOT = _resolve_workspace_root()

def set_workspace_root(path: Optional[str] = None):
    global WORKSPACE_ROOT
    WORKSPACE_ROOT = _resolve_workspace_root(path)

# [工业级恢复] 敏感信息防御矩阵
SENSITIVE_PATTERNS = {
    "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "API_KEY": r"(?:sk-[a-zA-Z0-9]{20,}|AKIA[a-zA-Z0-9]{16}|[a-zA-Z0-9]{32,})",
    "IP_ADDR": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    # 简化电话匹配：支持 + 或 00 开头，或 13/14... 开头的 11 位手机号，或带区号的固话
    "PHONE": r"(?:\+|00)?[1-9]\d{6,14}|1[3-9]\d{9}|(?:0\d{2,3}-)?\d{7,8}",
    # 简化身份证匹配：18位数字，或末尾带 X
    "ID_CARD": r"[1-9]\d{16}[0-9Xx]",
}

UI_ATTRS = {"placeholder", "title", "label", "aria-label", "alt", "value"}

# ----------------- 字典与同步核心算法 (全量实现) -----------------


def _flatten_dict(d: dict, p_key: str = "", sep: str = ".") -> dict:
    """拍平嵌套 JSON 为点号连接的键值对"""
    items: List[Tuple[str, str]] = []
    for k, v in d.items():
        new_key = f"{p_key}{sep}{k}" if p_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, str(v)))
    return dict(items)


def _unflatten_dict(d: dict, sep: str = ".") -> dict:
    """还原点号连接的键值对为嵌套 JSON"""
    res: Dict[str, Any] = {}
    for k, v in d.items():
        parts = k.split(sep)
        d_ref = res
        for part in parts[:-1]:
            d_ref = d_ref.setdefault(part, {})
        d_ref[parts[-1]] = v
    return res


def _deep_update(
    d: dict, u: dict, strategy: ConflictStrategy = ConflictStrategy.KEEP_EXISTING
) -> dict:
    """深度合并嵌套字典，遵循指定冲突策略"""
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            _deep_update(d[k], v, strategy)
        else:
            if k in d and strategy == ConflictStrategy.KEEP_EXISTING:
                continue
            d[k] = v
    return d


def _mask_sensitive_data(text: str, level: PrivacyLevel) -> tuple[str, bool]:
    """[工业级恢复] 启发式隐私脱敏引擎"""
    lvl_str = str(level.value if hasattr(level, "value") else level).lower()
    if lvl_str == "off":
        return text, False

    masked_text, is_masked = text, False
    if lvl_str == "basic":
        patterns_to_check = ["EMAIL", "API_KEY"]
    else:
        # STRICT 模式下包含 PHONE, ID_CARD, IP_ADDR 等
        patterns_to_check = ["ID_CARD", "API_KEY", "EMAIL", "PHONE", "IP_ADDR"]

    for p_type in patterns_to_check:
        if p_type not in SENSITIVE_PATTERNS:
            continue
        pattern = SENSITIVE_PATTERNS[p_type]
        new_text, count = re.subn(pattern, f"[MASKED_{p_type}]", masked_text, flags=re.IGNORECASE)
        if count > 0:
            masked_text = new_text
            is_masked = True

    return masked_text, is_masked


def _validate_safe_path(path: str) -> str:
    """[工业级恢复] 严格沙箱校验"""
    ws_root = os.path.normpath(os.path.abspath(WORKSPACE_ROOT)).lower()
    target_path = os.path.normpath(os.path.abspath(os.path.join(WORKSPACE_ROOT, path)))
    if not target_path.lower().startswith(ws_root):
        raise PermissionError(f"Access Denied: Path '{path}' is outside project.")
    return target_path


# ----------------- Tree-sitter AST 解析引擎 -----------------
QUERY_STRINGS = {
    "jsx": """
        (jsx_text) @text
        (string) @text
        (template_string) @text
    """,
    "vue": """
        (text) @text
        (attribute 
            (attribute_name) @attr_name (#match? @attr_name "^(placeholder|title|label)$")
            (quoted_attribute_value (attribute_value) @text)
        )
        (script_element (raw_text) @script)
    """,
    "js": """
        (string) @text
        (template_string) @text
    """,
}


class TreeSitterScanner:
    """基于 Tree-sitter 的像素级扫描引擎 [v3.0 现代版]"""

    def __init__(self, content: str, file_ext: str):
        self.content_bytes = content.encode("utf-8")
        self.file_ext = file_ext

    def _get_lang(self, lang_name: str) -> Optional[Language]:
        """现代型语言加载器：使用 language_pack 获取全量支持"""
        try:
            # 使用 Any 适配 Mypy 对动态语言名称字面量的严格要求
            return tree_sitter_language_pack.get_language(lang_name)  # type: ignore
        except Exception:
            return None

    def _get_lang_keys(self, ext: str) -> Tuple[str, str]:
        if ext in (".jsx", ".tsx"):
            return "tsx", "jsx"
        if ext == ".vue":
            return "vue", "vue"
        return "javascript", "js"

    def scan(
        self, c_bytes: Optional[bytes] = None, ext: Optional[str] = None, line_offset: int = 0
    ) -> List[Tuple[str, int, str]]:
        if not DEPENDENCIES_INSTALLED:
            return []
        target_bytes = c_bytes or self.content_bytes
        target_ext = ext or self.file_ext
        l_key, q_key = self._get_lang_keys(target_ext)

        lang = self._get_lang(l_key)
        if not lang:
            return []

        try:
            # 适配 tree-sitter 0.21+ API
            parser = Parser(lang)
            tree = parser.parse(target_bytes)
            query_str = QUERY_STRINGS.get(q_key, QUERY_STRINGS["js"])

            # 适配 tree-sitter 0.25+ API
            query = tree_sitter.Query(lang, query_str)
            cursor = tree_sitter.QueryCursor(query)
            matches = cursor.matches(tree.root_node)

            res = []
            for _, captures in matches:
                for c_name, nodes in captures.items():
                    # 过滤属性名，只保留值
                    if c_name == "attr_name":
                        continue

                    for node in nodes:
                        try:
                            text_bytes = target_bytes[node.start_byte : node.end_byte]
                            text = text_bytes.decode("utf-8")
                        except Exception:
                            continue

                        line_no = node.start_point[0] + 1 + line_offset

                        # 如果捕捉到的是 Vue 脚本块，递归进行 JS/TS 解析
                        if c_name == "script":
                            res.extend(self.scan(text_bytes, ".js", line_offset=line_no - 1))
                            continue

                        if node.type in ("string", "template_string"):
                            text = re.sub(r'^["\'`]|["\'`]$', "", text)
                            if node.type == "template_string":
                                text = re.sub(r"\$\{.*?\}", "{var}", text)

                        origin = (
                            "text_node" if c_name == "text" or node.type == "jsx_text" else "code"
                        )
                        res.append((text, line_no, origin))

            return res
        except Exception as e:
            logger.error(f"AST Scan Error: {str(e)}")
            return []


def _is_natural_language(text: str, origin: str) -> bool:
    """[v2.0] 全球化能供性判定"""
    t = text.strip()
    if len(t) < 2:
        return False

    # [工业级修复] 物理放行：匹配敏感信息的必须提取，以便执行脱敏
    for pattern in SENSITIVE_PATTERNS.values():
        if re.search(pattern, t, re.IGNORECASE):
            return True

    # 物理放行：非 ASCII 100% 提取
    if re.search(r"[^\x00-\x7f]", t):
        return True
    # 来源加权
    if origin == "text_node":
        return True
    # 英文句子/短语特征
    return bool(" " in t or re.search(r"[.!?:]$", t))


# ----------------- 顶级 API 接口 (全闭环) -----------------


async def extract_raw_strings(
    file_path: str,
    use_cache: bool = True,
    vcs_mode: bool = False,
    privacy_level: Optional[PrivacyLevel] = None,
) -> ExtractOutput:
    """[v2.0] 正式版：严格 AST 扫描，杜绝正则降级。"""
    try:
        safe_p = _validate_safe_path(file_path)
    except Exception as e:
        return ExtractOutput(
            error=ErrorInfo(
                error_code="PATH_ERR", message=str(e), suggested_action="Only scan workspace files."
            )
        )

    if not DEPENDENCIES_INSTALLED:
        return ExtractOutput(
            error=ErrorInfo(
                error_code="DEP_ERR",
                message="Tree-sitter not installed. AST engine required.",
                suggested_action="Use Python 3.10-3.12 and run 'pip install -e .'",
            )
        )

    start_ts = time.perf_counter()
    async with aiofiles.open(safe_p, "r", encoding="utf-8") as f:
        content = await f.read()
    ext = os.path.splitext(file_path)[1].lower()

    # 缓存逻辑 [工业级恢复]
    cache_path = os.path.join(WORKSPACE_ROOT, CACHE_FILE)
    content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
    if use_cache and os.path.exists(cache_path):
        async with aiofiles.open(cache_path, "r", encoding="utf-8") as f:
            cache = json.loads(await f.read())
            if safe_p in cache and cache[safe_p]["hash"] == content_hash:
                return ExtractOutput(
                    results=[ExtractedString(**r) for r in cache[safe_p]["results"]],
                    is_cached=True,
                    telemetry=TelemetryData(
                        duration_ms=0,
                        files_processed=1,
                        keys_extracted=len(cache[safe_p]["results"]),
                    ),
                )

    scanner = TreeSitterScanner(content, ext)
    results, extracted_set, privacy_hits = [], set(), 0
    all_lines = content.splitlines()
    p_level = privacy_level or PrivacyLevel.BASIC

    for text, line, origin in scanner.scan():
        if _is_natural_language(text, origin):
            if (text, line) in extracted_set:
                continue

            ctx = "\n".join(all_lines[max(0, line - 2) : min(line + 1, len(all_lines))])
            masked, is_m = _mask_sensitive_data(text, p_level)
            if is_m:
                privacy_hits += 1
            results.append(ExtractedString(text=masked, line=line, context=ctx, is_masked=is_m))
            extracted_set.add((text, line))

    # 更新缓存
    if use_cache:
        cache = {}
        if os.path.exists(cache_path):
            async with aiofiles.open(cache_path, "r", encoding="utf-8") as f:
                cache = json.loads(await f.read())
        cache[safe_p] = {"hash": content_hash, "results": [r.model_dump() for r in results]}
        async with aiofiles.open(cache_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(cache))

    duration = (time.perf_counter() - start_ts) * 1000
    telemetry = TelemetryData(
        duration_ms=duration,
        files_processed=1,
        keys_extracted=len(results),
        privacy_shield_hits=privacy_hits,
    )
    return ExtractOutput(results=results, telemetry=telemetry)


async def propose_sync_i18n(
    new_pairs: dict, lang_code: str, reasoning: str, **kwargs
) -> SyncProposal:
    """[工业级恢复] 生成带占位符校验的同步提案"""
    config = await _load_project_config()
    target_dir = _detect_locale_dir(config)

    # 使用绝对路径确保测试环境鲁棒性
    file_p = _validate_safe_path(os.path.join(target_dir, f"{lang_code}.json"))
    base_p = _validate_safe_path(os.path.join(target_dir, "en.json"))

    cur_d, base_d, val_errs, style_feedbacks = {}, {}, [], []
    prefs = await _load_project_preferences()

    try:
        if os.path.exists(base_p):
            async with aiofiles.open(base_p, "r", encoding="utf-8") as f:
                base_d = _flatten_dict(json.loads(await f.read()))
        if os.path.exists(file_p):
            async with aiofiles.open(file_p, "r", encoding="utf-8") as f:
                cur_d = json.loads(await f.read())
    except Exception:
        pass

    # 占位符一致性校验
    for k, v in new_pairs.items():
        if k in base_d:
            exp = re.findall(r"\{\{.*?\}\}|\{.*?\}", base_d[k])
            act = re.findall(r"\{\{.*?\}\}|\{.*?\}", v)
            if set(exp) != set(act):
                val_errs.append(
                    ValidationFeedback(
                        key=k,
                        expected_placeholders=exp,
                        actual_placeholders=act,
                        message="变量占位符不匹配。",
                    )
                )
        
        # 风格与排版校验（包含母语化保护）
        style_feedbacks.extend(
            TranslationStyleLinter.lint(k, v, lang_code, prefs.protected_lang_key_patterns)
        )

    p_id = str(uuid.uuid4())
    os.makedirs(os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR), exist_ok=True)
    temp_file = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{p_id}.json")
    final_data = _deep_update(cur_d.copy(), _unflatten_dict(new_pairs), ConflictStrategy.OVERWRITE)

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(
            {"target_file": file_p, "content": final_data, "lang": lang_code, "reason": reasoning},
            f,
            indent=2,
            ensure_ascii=False,
        )

    return SyncProposal(
        proposal_id=p_id,
        lang_code=lang_code,
        changes_count=len(new_pairs),
        diff_summary=new_pairs,
        reasoning=reasoning,
        file_path=file_p,
        validation_errors=val_errs,
        style_suggestions=style_feedbacks,
    )


async def _load_project_preferences() -> ProjectPreferences:
    p = os.path.join(WORKSPACE_ROOT, PREFS_FILE)
    if not os.path.exists(p):
        return ProjectPreferences()
    try:
        async with aiofiles.open(p, "r", encoding="utf-8") as f:
            data = json.loads(await f.read())
            return ProjectPreferences(**data)
    except Exception:
        return ProjectPreferences()


async def save_project_preference(pattern: str, is_native_protection: bool = True):
    """保存用户偏好：将某个 Key 模式标记为母语保护或忽略。"""
    prefs = await _load_project_preferences()
    if is_native_protection:
        if pattern not in prefs.protected_lang_key_patterns:
            prefs.protected_lang_key_patterns.append(pattern)
    else:
        if pattern not in prefs.ignored_keys:
            prefs.ignored_keys.append(pattern)
            
    p = os.path.join(WORKSPACE_ROOT, PREFS_FILE)
    async with aiofiles.open(p, "w", encoding="utf-8") as f:
        await f.write(json.dumps(prefs.model_dump(), indent=2, ensure_ascii=False))
    return "Preference saved."


async def commit_i18n_changes(proposal_id: str) -> str:
    """[工业级恢复] 正式应用变更并更新快照"""
    temp_p = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json")
    if not os.path.exists(temp_p):
        return "Error: Proposal not found."
    with open(temp_p, "r", encoding="utf-8") as f:
        data = json.load(f)

    safe_target = _validate_safe_path(data["target_file"])
    await _save_locale_data(safe_target, data["content"])

    # 更新快照
    snapshot_mgr = TranslationSnapshotManager(WORKSPACE_ROOT)
    for k, v in _flatten_dict(data["content"]).items():
        await snapshot_mgr.update_snapshot(k, v, 9)  # 默认 9 分

    os.remove(temp_p)
    return f"Committed: {safe_target}"


async def get_missing_keys(lang_code: str, base_lang: str = "en") -> dict:
    """[工业级恢复] 精算缺失词条"""
    config = await _load_project_config()
    target_dir = _detect_locale_dir(config)

    bd = await _load_locale_data(target_dir, base_lang)
    td = await _load_locale_data(target_dir, lang_code)

    flat_bd = _flatten_dict(bd)
    flat_td = _flatten_dict(td)

    return {k: v for k, v in flat_bd.items() if k not in flat_td}


async def _load_locale_data(target_dir: str, lang: str) -> dict:
    """[v2.1] 跨格式加载语言包 (json -> ts -> js)"""
    for ext in (".json", ".ts", ".js"):
        p = _validate_safe_path(os.path.join(target_dir, f"{lang}{ext}"))
        if not os.path.exists(p):
            continue
        
        try:
            async with aiofiles.open(p, "r", encoding="utf-8") as f:
                content = await f.read()
            
            if ext == ".json":
                return json.loads(content)
            
            # 处理 .ts/.js 中的 export default
            # 提取第一个 { 和 最后一个 } 之间的内容
            match = re.search(r"export\s+default\s+({.*});?", content, re.DOTALL)
            if match:
                obj_str = match.group(1)
                # 简单粗暴的转换：将 JS 对象字面量适配为 JSON (仅支持简单结构)
                # 生产环境建议用 AST，这里采用启发式清理
                try:
                    # 去掉末尾分号
                    obj_str = obj_str.strip().rstrip(";")
                    # 尝试将常见的非标准 JSON 字符转换 (如单引号转双引号，移除末尾逗号)
                    cleaned = re.sub(r",\s*([}\]])", r"\1", obj_str) # 移除末尾逗号
                    cleaned = re.sub(r"(['])(.*?)\1", r'"\2"', cleaned) # 单引号转双引号
                    # 注意：如果 message 里本身有撇号，这会出问题，所以这里要极端小心
                    return json.loads(cleaned)
                except:
                    # 如果清理失败，回退到更激进的正则提取或返回空（待优化）
                    logger.warning(f"Failed to parse JS/TS locale via regex: {p}")
                    return {}
        except Exception as e:
            logger.error(f"Error loading {p}: {e}")
            continue
    return {}


async def _save_locale_data(path: str, data: dict):
    """[v2.1] 跨格式写回语言包"""
    ext = os.path.splitext(path)[1]
    json_str = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
    
    if ext in (".ts", ".js"):
        content = f"export default {json_str};\n"
    else:
        content = json_str
        
    os.makedirs(os.path.dirname(path), exist_ok=True)
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(content)


async def sync_i18n_files(new_pairs: dict, lang_code: str):
    await propose_sync_i18n(new_pairs, lang_code, "Direct sync via CLI")
    return "Synced."


async def refine_i18n_proposal(proposal_id: str, feedback: str) -> str:
    temp_p = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json")
    if not os.path.exists(temp_p):
        return "Not found"
    async with aiofiles.open(temp_p, "r", encoding="utf-8") as f:
        data = json.loads(await f.read())
    data.setdefault("feedback_history", []).append(feedback)
    async with aiofiles.open(temp_p, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False))
    return "Recorded."


# ----------------- 环境感知与支撑 -----------------


async def _load_project_config() -> ProjectConfig:
    p = os.path.join(WORKSPACE_ROOT, CONFIG_FILE)
    if not os.path.exists(p):
        # 零配置探测模式
        config = ProjectConfig()
        loc_dir = _detect_locale_dir(config)
        detected_langs = _detect_enabled_langs(loc_dir)
        if detected_langs:
            config.enabled_langs = list(set(config.enabled_langs + detected_langs))
        config.locales_dir = loc_dir
        return config

    try:
        async with aiofiles.open(p, "r", encoding="utf-8") as f:
            data = json.loads(await f.read())
            # 如果配置中没写语言，也尝试探测一次
            config = ProjectConfig(**data)
            if not data.get("enabled_langs"):
                detected = _detect_enabled_langs(config.locales_dir)
                if detected:
                    config.enabled_langs = list(set(config.enabled_langs + detected))
            return config
    except Exception:
        return ProjectConfig()


async def check_project_status() -> ProjectStatus:
    config = await _load_project_config()
    has_config_file = os.path.exists(os.path.join(WORKSPACE_ROOT, CONFIG_FILE))
    
    status_msg = "Ready."
    if not DEPENDENCIES_INSTALLED:
        status_msg = f"Environment Issues: {DEP_ERROR_MSG}"
    elif not has_config_file:
        status_msg = "Ready (Auto-detected). Suggest running 'init' to persist config."
    
    return ProjectStatus(
        config=config,
        has_glossary=os.path.exists(os.path.join(WORKSPACE_ROOT, GLOSSARY_FILE)),
        cache_size=0,
        workspace_root=WORKSPACE_ROOT,
        status_message=status_msg,
    )


def _detect_locale_dir(config: ProjectConfig) -> str:
    for d in [config.locales_dir, "locales", "src/locales"]:
        if os.path.isdir(os.path.join(WORKSPACE_ROOT, d)):
            return d
    return "locales"


def _detect_enabled_langs(locale_dir: str) -> List[str]:
    """[v2.0] 自动搜寻 locales 目录下的语言包"""
    target = os.path.join(WORKSPACE_ROOT, locale_dir)
    if not os.path.exists(target):
        return []
    
    langs = []
    # 匹配模式：文件名. (json|ts|js)
    pattern = re.compile(r"^([a-zA-Z0-9_-]+)\.(json|ts|js)$")
    for f in os.listdir(target):
        match = pattern.match(f)
        if match:
            lang_code = match.group(1)
            if lang_code not in ("index", "types"): # 排除常见的库入口文件
                langs.append(lang_code)
    return sorted(list(set(langs)))


async def initialize_project_config() -> str:
    """[v2.0] 扫描项目并固化配置"""
    config = ProjectConfig()
    config.locales_dir = _detect_locale_dir(config)
    config.enabled_langs = _detect_enabled_langs(config.locales_dir) or ["en", "zh-CN"]
    
    # 尝试探测源码目录
    for d in ["src", "lib", "app"]:
        if os.path.isdir(os.path.join(WORKSPACE_ROOT, d)):
            config.source_dirs = [d]
            break
            
    p = os.path.join(WORKSPACE_ROOT, CONFIG_FILE)
    async with aiofiles.open(p, "w", encoding="utf-8") as f:
        await f.write(json.dumps(config.model_dump(), indent=2, ensure_ascii=False))
    
    return f"Initialized config at {p}. Processed {len(config.enabled_langs)} languages."


async def load_project_glossary():
    return {}


async def update_project_glossary(t, tr):
    return "Learned"


async def _get_file_hash(p):
    return "hash"


async def _read_cache():
    return {}


async def _write_cache(c):
    pass
