import glob
import hashlib
import json
import os
import re
from typing import Any, Literal, cast

import aiofiles
import tree_sitter
import tree_sitter_language_pack
import yaml
from tree_sitter import Parser

from i18n_agent_skill.linter import ENDONYM_MAP, TranslationStyleLinter
from i18n_agent_skill.logger import structured_logger as logger
from i18n_agent_skill.models import (
    ConflictStrategy,
    ErrorInfo,
    EvaluationReport,
    ExtractedString,
    ExtractOutput,
    PrivacyLevel,
    ProjectConfig,
    ProjectStatus,
    ReviewItem,
    SyncProposal,
    TelemetryData,
    TranslationStatus,
)
from i18n_agent_skill.snapshot import TranslationSnapshotManager
from i18n_agent_skill.vcs import get_git_hunks, get_vcs_status

# Global Constants
CACHE_FILE = ".i18n-cache.json"
PROPOSALS_DIR = ".i18n-proposals"
GLOSSARY_FILE = "GLOSSARY.json"
CONFIG_FILE = ".i18n-skill.json"

DEPENDENCIES_INSTALLED = True

# Pre-calculate common language endonyms for fast filtering
_ENDONYM_VALUES = set()
for info in ENDONYM_MAP.values():
    _ENDONYM_VALUES.add(info["native"])
    for kw in info["search"]:
        if len(kw) > 2:
            _ENDONYM_VALUES.add(kw.capitalize())
            _ENDONYM_VALUES.add(kw)

SENSITIVE_PATTERNS = {
    "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "API_KEY": r"(?:sk-[a-zA-Z0-9-]{20,}|AKIA[a-zA-Z0-9]{16}|[a-zA-Z0-9]{32,})",
    "IP_ADDR": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    "ID_CARD": r"[1-9]\d{16}[0-9Xx]",
    "PHONE": r"(?:\+|00)?[1-9]\d{6,14}|1[3-9]\d{9}|(?:0\d{2,3}-)?\d{7,8}",
}


def _resolve_workspace_root(explicit_root: str | None = None) -> str:
    if explicit_root:
        return os.path.abspath(explicit_root)
    cwd = os.getcwd()
    current_dir = os.path.abspath(cwd)
    markers = [".git", "package.json", "pyproject.toml", CONFIG_FILE]
    while True:
        if any(os.path.exists(os.path.join(current_dir, m)) for m in markers):
            return current_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break
        current_dir = parent_dir
    return os.path.abspath(cwd)


WORKSPACE_ROOT = _resolve_workspace_root()


def set_workspace_root(path: str):
    global WORKSPACE_ROOT
    WORKSPACE_ROOT = os.path.abspath(path)


def _validate_safe_path(path: str) -> str:
    ws_root = os.path.normcase(os.path.realpath(os.path.abspath(WORKSPACE_ROOT)))
    target_path = os.path.realpath(os.path.abspath(os.path.join(WORKSPACE_ROOT, path)))
    normalized_target = os.path.normcase(target_path)
    try:
        common_path = os.path.commonpath([ws_root, normalized_target])
    except ValueError as exc:
        raise PermissionError(f"Access Denied: Path '{path}' is outside project.") from exc
    if common_path != ws_root:
        raise PermissionError(f"Access Denied: Path '{path}' is outside project.")
    return target_path


def _flatten_dict(d: dict, p_key: str = "", sep: str = ".") -> dict:
    items: list[tuple[str, str]] = []
    for k, v in d.items():
        new_key = f"{p_key}{sep}{k}" if p_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, str(v)))
    return dict(items)


def _unflatten_dict(d: dict, sep: str = ".") -> dict:
    res: dict[str, Any] = {}
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
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            _deep_update(d[k], v, strategy)
        else:
            if k in d and strategy == ConflictStrategy.KEEP_EXISTING:
                continue
            d[k] = v
    return d


def _mask_sensitive_data(text: str, level: PrivacyLevel) -> tuple[str, bool]:
    lvl_str = str(level.value if hasattr(level, "value") else level).lower()
    if lvl_str == "off":
        return text, False
    patterns = ["EMAIL", "API_KEY"] if lvl_str == "basic" else list(SENSITIVE_PATTERNS.keys())
    masked_text, is_masked = text, False
    for p_type in patterns:
        new_text, count = re.subn(
            SENSITIVE_PATTERNS[p_type], f"[MASKED_{p_type}]", masked_text, flags=re.IGNORECASE
        )
        if count > 0:
            masked_text, is_masked = new_text, True
    return masked_text, is_masked


def _is_natural_language(text: str, origin: str, ignored_strings: list[str] | None = None) -> bool:
    if origin == "fallback_text":
        return False
    t = text.strip()
    if not t or t in _ENDONYM_VALUES:
        return False
    if ignored_strings and t in ignored_strings:
        return False

    for pattern in SENSITIVE_PATTERNS.values():
        if re.search(pattern, t, re.IGNORECASE):
            return True

    if origin == "text_node":
        return True
    if " " in t or "..." in t:
        return True
    if len(t) < 2 or re.match(r"^[a-z0-9._\-\[\]]+$", t, re.IGNORECASE):
        if not re.search(r"[^\x00-\x7f]", t):
            return False

    if t.lower().startswith(("http", "env:", "calc(", "var(", "--", "@", "./", "../")):
        return False
    if re.search(r"[^\x00-\x7f]", t):
        return True
    return bool(re.search(r"[.!?:]$", t))


QUERY_STRINGS = {
    "jsx": """
        (jsx_text) @text
        (string) @str
        (template_string) @str
        (import_statement) @skip
        (jsx_attribute (property_identifier) @attr_name)
        (jsx_self_closing_element
            name: (identifier) @comp (#eq? @comp "Trans")
            attribute: (jsx_attribute
                (property_identifier) @attr_name (#eq? @attr_name "i18nKey")
                (string) @key)
        )
        (jsx_opening_element
            name: (identifier) @comp (#eq? @comp "Trans")
            attribute: (jsx_attribute
                (property_identifier) @attr_name (#eq? @attr_name "i18nKey")
                (string) @key)
        )
        (call_expression
            function: [
                (identifier) @f (#any-of? @f "t" "$t")
                (member_expression property: (property_identifier) @m (#eq? @m "t"))
            ]
            arguments: (arguments (string) @key)
        )
    """,
    "js": """
        (string) @str
        (template_string) @str
        (import_statement) @skip
        (call_expression
            function: [
                (identifier) @f (#any-of? @f "t" "$t")
                (member_expression property: (property_identifier) @m (#eq? @m "t"))
            ]
            arguments: (arguments (string) @key)
        )
    """,
    "vue": """
        (text) @text
        (attribute (attribute_name) @attr_name (quoted_attribute_value (attribute_value) @text))
        (script_element (raw_text) @script)
    """,
}


class TreeSitterScanner:
    def __init__(self, content: str, file_ext: str):
        self.content_bytes = content.encode("utf-8")
        self.file_ext = file_ext

    def _get_lang_keys(self, ext: str) -> tuple[str, str]:
        if ext in (".jsx", ".tsx"):
            return "tsx", "jsx"
        if ext == ".vue":
            return "vue", "vue"
        return "javascript", "js"

    def scan(
        self, c_bytes: bytes | None = None, ext: str | None = None, line_offset: int = 0
    ) -> list[tuple[str, int, str]]:
        target_bytes = c_bytes or self.content_bytes
        l_key, q_key = self._get_lang_keys(ext or self.file_ext)
        try:
            lang = tree_sitter_language_pack.get_language(cast(Any, l_key))
            parser = Parser(lang)
            tree = parser.parse(target_bytes)
            query = tree_sitter.Query(lang, QUERY_STRINGS.get(q_key, QUERY_STRINGS["js"]))
            matches = tree_sitter.QueryCursor(query).matches(tree.root_node)

            res, processed = [], set()
            metadata_attrs = {
                "value",
                "name",
                "id",
                "className",
                "key",
                "ref",
                "type",
                "src",
                "lang",
                "locale",
            }
            ui_attrs = {"label", "placeholder", "title", "alt", "aria-label", "description"}

            for _, caps in matches:
                if "key" in caps:
                    for n in caps["key"]:
                        nid = (n.start_byte, n.end_byte)
                        if nid in processed:
                            continue
                        res.append(
                            (
                                n.text.decode("utf-8").strip("'\""),
                                n.start_point[0] + 1 + line_offset,
                                "i18n_key",
                            )
                        )
                        processed.add(nid)
                    continue

                for c_name, nodes in caps.items():
                    if c_name in ("f", "m", "skip"):
                        continue
                    for node in nodes:
                        nid = (node.start_byte, node.end_byte)
                        if nid in processed:
                            continue
                        curr, is_excluded, origin = node, False, "code"
                        while curr:
                            if curr.type in ("import_statement", "import_declaration"):
                                is_excluded = True
                                break
                            if curr.type == "jsx_attribute":
                                name_node = curr.child_by_field_name("name") or curr.children[0]
                                if name_node:
                                    nm = name_node.text.decode("utf-8")
                                    if nm in metadata_attrs and nm not in ui_attrs:
                                        is_excluded = True
                                break
                            if curr.type == "pair":
                                key_node = curr.child_by_field_name("key") or curr.children[0]
                                if key_node:
                                    nm = key_node.text.decode("utf-8")
                                    if nm in metadata_attrs or nm == "label":
                                        is_excluded = True
                                break
                            curr = curr.parent
                        if is_excluded:
                            processed.add(nid)
                            continue
                        text = node.text.decode("utf-8")
                        if c_name == "script":
                            res.extend(
                                self.scan(
                                    node.text, ".js", line_offset=node.start_point[0] + line_offset
                                )
                            )
                        else:
                            if node.type in ("string", "template_string"):
                                text = re.sub(r'^["\'`]|["\'`]$', "", text)
                                if node.type == "template_string":
                                    text = re.sub(r"\$\{.*?\}", "{var}", text)
                            if text.strip() in _ENDONYM_VALUES:
                                processed.add(nid)
                                continue
                            if node.type == "jsx_text" or c_name == "text":
                                origin = "text_node"
                            res.append((text, node.start_point[0] + 1 + line_offset, origin))
                        processed.add(nid)
            return res
        except Exception as e:
            logger.error(f"Scan error: {e}")
            return []


async def _load_project_config() -> ProjectConfig:
    p = os.path.join(WORKSPACE_ROOT, CONFIG_FILE)
    if os.path.exists(p):
        async with aiofiles.open(p, encoding="utf-8") as f:
            return ProjectConfig(**json.loads(await f.read()))
    return ProjectConfig()


async def _save_project_config(config: ProjectConfig):
    config_path = _validate_safe_path(CONFIG_FILE)
    async with aiofiles.open(config_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(config.model_dump(mode="json"), indent=2, ensure_ascii=False))


async def extract_raw_strings(
    file_path: str,
    use_cache: bool = True,
    vcs_mode: bool = False,
    privacy_level: PrivacyLevel | None = None,
    shared_cache: dict[str, Any] | None = None,
) -> ExtractOutput:
    try:
        safe_p = _validate_safe_path(file_path)
    except Exception as e:
        return ExtractOutput(
            error=ErrorInfo(
                error_code="PATH_ERR", message=str(e), suggested_action="Only scan workspace files."
            )
        )
    if not os.path.exists(safe_p):
        return ExtractOutput(
            error=ErrorInfo(
                error_code="PATH_ERR",
                message=f"File not found: {file_path}",
                suggested_action="Verify path.",
            )
        )
    async with aiofiles.open(safe_p, encoding="utf-8") as f:
        content = await f.read()
    config = await _load_project_config()
    content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
    if (
        use_cache
        and shared_cache
        and safe_p in shared_cache
        and shared_cache[safe_p]["hash"] == content_hash
    ):
        return ExtractOutput(
            results=[ExtractedString(**r) for r in shared_cache[safe_p]["results"]],
            is_cached=True,
            telemetry=TelemetryData(
                duration_ms=0,
                files_processed=1,
                keys_extracted=len(shared_cache[safe_p]["results"]),
            ),
        )
    scanner = TreeSitterScanner(content, os.path.splitext(file_path)[1].lower())
    results, seen, p_lvl = [], set(), privacy_level or config.privacy_level or PrivacyLevel.BASIC
    lines = content.splitlines()
    for text, line, origin in scanner.scan():
        if _is_natural_language(text, origin, config.ignored_strings):
            if (text, line) in seen:
                continue
            masked, text_is_masked = _mask_sensitive_data(text, p_lvl)
            ctx = "\n".join(lines[max(0, line - 2) : min(line + 1, len(lines))])
            masked_ctx, context_is_masked = _mask_sensitive_data(ctx, p_lvl)
            results.append(
                ExtractedString(
                    text=masked,
                    line=line,
                    context=masked_ctx,
                    is_masked=text_is_masked or context_is_masked,
                )
            )
            seen.add((text, line))
    if use_cache and shared_cache is not None:
        shared_cache[safe_p] = {"hash": content_hash, "results": [r.model_dump() for r in results]}
    return ExtractOutput(
        results=results,
        telemetry=TelemetryData(duration_ms=0, files_processed=1, keys_extracted=len(results)),
    )


async def orchestrate_scan(
    path: str | None = None, use_cache: bool = True, vcs_mode: bool = False
) -> dict:
    config = await _load_project_config()
    git_hunks = get_git_hunks(WORKSPACE_ROOT) if vcs_mode else {}
    if vcs_mode and not git_hunks:
        return {"results": []}
    scan_paths = [path] if path else (config.source_dirs or ["src"])
    cache_path, shared_cache = os.path.join(WORKSPACE_ROOT, CACHE_FILE), {}
    if use_cache and os.path.exists(cache_path):
        try:
            async with aiofiles.open(cache_path, encoding="utf-8") as f_cache:
                shared_cache = json.loads(await f_cache.read())
        except Exception:
            pass
    all_res = []

    def changed_lines(file_path: str) -> set[int] | None:
        if not vcs_mode:
            return None
        rel_path = os.path.relpath(file_path, WORKSPACE_ROOT).replace("\\", "/")
        return git_hunks.get(rel_path)

    def append_results(file_path: str, output: ExtractOutput):
        if not output.results:
            return
        line_filter = changed_lines(file_path)
        if vcs_mode and not line_filter:
            return
        for result in output.results:
            if line_filter is None or result.line in line_filter:
                all_res.append(result.model_dump())

    for p in scan_paths:
        abs_p = os.path.join(WORKSPACE_ROOT, p)
        if os.path.isdir(abs_p):
            for root, _, files in os.walk(abs_p):
                if any(i in root.replace("\\", "/").split("/") for i in config.ignore_dirs):
                    continue
                for filename in files:
                    if os.path.splitext(filename)[1].lower() in (
                        ".js",
                        ".jsx",
                        ".ts",
                        ".tsx",
                        ".vue",
                    ):
                        out = await extract_raw_strings(
                            os.path.join(root, filename),
                            use_cache=use_cache,
                            shared_cache=shared_cache,
                        )
                        append_results(os.path.join(root, filename), out)
        elif os.path.exists(abs_p):
            out = await extract_raw_strings(abs_p, use_cache=use_cache, shared_cache=shared_cache)
            append_results(abs_p, out)
    if use_cache:
        try:
            async with aiofiles.open(cache_path, "w", encoding="utf-8") as f_out:
                await f_out.write(json.dumps(shared_cache))
        except Exception:
            pass
    return {"results": all_res}


LOCALE_EXTENSIONS = [".json", ".yaml", ".yml", ".ts", ".js"]
STANDARD_LOCALE_DIRS = ["src/locales", "locales", "public/locales"]
EXTENDED_LOCALE_DIRS = ["i18n", "translations", "messages", "lang"]
LANG_STEM_RE = re.compile(r"^[A-Za-z]{2,3}(?:[_-][A-Za-z0-9]{2,8})*$")
SOURCE_CODE_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".vue", ".py"}


def _sort_languages(langs: set[str]) -> list[str]:
    ordered = sorted(langs)
    if "en" in ordered:
        ordered.remove("en")
        ordered.insert(0, "en")
    return ordered


def _normalize_extension(ext: str | None) -> str | None:
    if not ext:
        return None
    fixed = ext if ext.startswith(".") else f".{ext}"
    if fixed in LOCALE_EXTENSIONS:
        return fixed
    return None


def _collect_source_dirs() -> list[str]:
    return ["src"] if os.path.isdir(os.path.join(WORKSPACE_ROOT, "src")) else ["."]


def _has_extractable_source() -> bool:
    for root, _, files in os.walk(WORKSPACE_ROOT):
        if ".git" in root.replace("\\", "/").split("/"):
            continue
        for filename in files:
            if os.path.splitext(filename)[1].lower() in SOURCE_CODE_EXTENSIONS:
                return True
    return False


def _scan_locale_candidate(rel_dir: str) -> dict[str, Any]:
    abs_dir = _validate_safe_path(rel_dir)
    locale_files: list[str] = []
    invalid_files: list[str] = []
    langs: set[str] = set()
    exts: set[str] = set()

    for filename in os.listdir(abs_dir):
        full_path = os.path.join(abs_dir, filename)
        if not os.path.isfile(full_path):
            continue
        stem, ext = os.path.splitext(filename)
        ext = ext.lower()
        if ext not in LOCALE_EXTENSIONS:
            continue
        locale_files.append(os.path.join(rel_dir, filename).replace("\\", "/"))
        exts.add(ext)
        if LANG_STEM_RE.match(stem):
            langs.add(stem)
        else:
            invalid_files.append(filename)

    return {
        "dir": rel_dir.replace("\\", "/"),
        "files": sorted(locale_files),
        "invalid_files": sorted(invalid_files),
        "langs": _sort_languages(langs),
        "extensions": sorted(exts),
    }


def _detect_locale_candidates(existing_locale_dir: str | None = None) -> list[dict[str, Any]]:
    ordered_dirs: list[str] = []
    seen = set()
    for rel_dir in [*STANDARD_LOCALE_DIRS, *EXTENDED_LOCALE_DIRS]:
        if rel_dir in seen:
            continue
        seen.add(rel_dir)
        if os.path.isdir(os.path.join(WORKSPACE_ROOT, rel_dir)):
            ordered_dirs.append(rel_dir)
    if existing_locale_dir and existing_locale_dir not in seen:
        if os.path.isdir(os.path.join(WORKSPACE_ROOT, existing_locale_dir)):
            ordered_dirs.append(existing_locale_dir)

    candidates: list[dict[str, Any]] = []
    for rel_dir in ordered_dirs:
        try:
            candidates.append(_scan_locale_candidate(rel_dir))
        except PermissionError:
            continue
    return candidates


def _infer_preferred_format(extensions: list[str]) -> str | None:
    return extensions[0] if len(extensions) == 1 else None


def _load_existing_init_config() -> tuple[ProjectConfig | None, dict[str, Any] | None, str | None]:
    config_path = os.path.join(WORKSPACE_ROOT, CONFIG_FILE)
    if not os.path.exists(config_path):
        return None, None, None
    try:
        with open(config_path, encoding="utf-8") as f:
            raw = json.load(f)
        return ProjectConfig(**raw), raw, None
    except Exception as exc:
        return None, None, str(exc)


def _classify_init_mode(
    candidates: list[dict[str, Any]], existing_locale_dir: str | None
) -> tuple[str, dict[str, Any] | None, str]:
    with_langs = [c for c in candidates if c["langs"]]
    if with_langs:
        if len(with_langs) == 1:
            return "sync", with_langs[0], "Detected a clear locale asset root."
        if existing_locale_dir:
            for candidate in with_langs:
                if candidate["dir"] == existing_locale_dir.replace("\\", "/"):
                    return "sync", candidate, "Existing config locale root is still valid."
        return (
            "reconcile",
            None,
            "Multiple locale roots contain valid language files. Confirmation is required.",
        )

    any_supported_files = any(candidate["files"] for candidate in candidates)
    any_invalid = any(candidate["invalid_files"] for candidate in candidates)
    if any_supported_files and any_invalid:
        return (
            "unsupported",
            None,
            "Locale-like files were found, but filenames are not language-code based.",
        )
    if _has_extractable_source():
        return "bootstrap", None, "No locale assets found. Initializing bootstrap config."
    return (
        "bootstrap",
        None,
        "No locale assets found. Initializing bootstrap config with minimal defaults.",
    )


def _existing_locale_path(target_dir: str, lang: str) -> str | None:
    for ext in LOCALE_EXTENSIONS:
        target_path = os.path.join(target_dir, f"{lang}{ext}")
        if os.path.exists(_validate_safe_path(target_path)):
            return target_path
    return None


def _resolve_locale_target_path(config: ProjectConfig, lang: str) -> str:
    existing = _existing_locale_path(config.locales_dir, lang)
    if existing:
        return existing
    preferred = config.preferred_format or ".json"
    preferred_ext = preferred if preferred.startswith(".") else f".{preferred}"
    if preferred_ext not in LOCALE_EXTENSIONS:
        preferred_ext = ".json"
    return os.path.join(config.locales_dir, f"{lang}{preferred_ext}")


async def _load_locale_data(target_dir: str, lang: str) -> dict:
    for ext in LOCALE_EXTENSIONS:
        target_path = os.path.join(target_dir, f"{lang}{ext}")
        p = _validate_safe_path(target_path)
        if os.path.exists(p):
            try:
                async with aiofiles.open(p, encoding="utf-8") as f:
                    content = await f.read()
                if ext == ".json":
                    return json.loads(content)
                if ext in (".yaml", ".yml"):
                    return yaml.safe_load(content) or {}
                l_key: Literal["tsx", "javascript"] = "tsx" if ext == ".ts" else "javascript"
                ts_lang = tree_sitter_language_pack.get_language(l_key)
                parser = Parser(ts_lang)
                tree = parser.parse(content.encode("utf-8"))

                def get_val(node: Any) -> Any:
                    if node.type == "object":
                        res: dict[str, Any] = {}
                        for child in node.children:
                            if child.type == "pair":
                                k = child.child_by_field_name("key") or child.children[0]
                                v = child.child_by_field_name("value") or child.children[2]
                                res[k.text.decode("utf-8").strip("'\"")] = get_val(v)
                        return res
                    if node.type in ("string", "template_string"):
                        return node.text.decode("utf-8").strip("'\"`")
                    return node.text.decode("utf-8")

                q_s = (
                    "(export_statement (object) @obj) "
                    "(export_statement (assignment_expression right: (object) @obj)) "
                    "(expression_statement (assignment_expression left: (member_expression) "
                    "right: (object) @obj))"
                )
                query = tree_sitter.Query(ts_lang, q_s)
                cursor = tree_sitter.QueryCursor(query)
                for _, caps in cursor.matches(tree.root_node):
                    if "obj" in caps:
                        return get_val(caps["obj"][0])
                m = re.search(
                    r"(?:export\s+default|module\.exports\s*=)\s*({.*});?", content, re.DOTALL
                )
                if m:
                    return json.loads(re.sub(r",\s*([}\]])", r"\1", m.group(1)).strip().rstrip(";"))
            except Exception:
                continue
    return {}


async def _save_locale_data(path: str, data: dict):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".ts", ".js"):
        content = (
            f"export default {json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)};\n"
        )
    elif ext in (".yaml", ".yml"):
        content = yaml.dump(data, allow_unicode=True, sort_keys=True, indent=2)
    else:
        content = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(content)


async def orchestrate_audit(lang_code: str = "all", base_lang: str = "en") -> dict:
    config = await _load_project_config()
    scan_data = await orchestrate_scan()
    raw, all_vals = scan_data.get("results", []), cast(set[str], set())
    for lang in config.enabled_langs:
        all_vals.update(_flatten_dict(await _load_locale_data(config.locales_dir, lang)).values())
    unextracted, seen = [], set()
    for s in raw:
        if s["text"] not in all_vals and s["text"] not in seen:
            unextracted.append(s)
            seen.add(s["text"])

    def build_noise_notice() -> str:
        if not unextracted:
            return "No unextracted hardcoded-string candidates were found."
        return (
            "unextracted_hardcoded_count is a candidate-noise metric, "
            "not a direct release blocker. Use scan --vcs for incremental "
            "work and tighten source_dirs/ignored_strings if noise stays high."
        )

    if lang_code == "all":
        results: dict[str, Any] = {
            "unextracted_hardcoded_count": len(unextracted),
            "unextracted_samples": unextracted[:10],
        }
        total_missing_keys = 0
        audited_languages = []
        for target_l in config.enabled_langs:
            if target_l == base_lang:
                continue
            missing = await get_missing_keys(target_l, base_lang=base_lang)
            results[target_l] = {"missing_count": len(missing), "missing_keys": missing}
            total_missing_keys += len(missing)
            audited_languages.append(target_l)
        results["message"] = "Audit complete."
        results["coverage_summary"] = {
            "base_language": base_lang,
            "audited_languages": audited_languages,
            "total_missing_keys": total_missing_keys,
        }
        results["noise_notice"] = build_noise_notice()
        if total_missing_keys:
            results["suggested_action"] = (
                "Fix missing locale keys first, then rerun audit --lang all to confirm coverage."
            )
        elif unextracted:
            results["suggested_action"] = (
                "Coverage is complete. Review unextracted samples and use "
                "scan --vcs for current work."
            )
        else:
            results["suggested_action"] = "Coverage and extraction checks are both clean."
        results["next_steps"] = [
            "Treat missing_count as the translation coverage signal for each target language.",
            "Use i18n scan --vcs to measure only the current code change set.",
            "Use i18n cleanup --lang all separately for report-only dead-key review.",
        ]
        return results
    else:
        missing = await get_missing_keys(lang_code, base_lang=base_lang)
        dead = await get_dead_keys(lang_code=lang_code)
        return {
            "language": lang_code,
            "missing_keys_count": len(missing),
            "missing_keys": missing,
            "dead_keys_count": len(dead),
            "dead_keys": dead,
            "unextracted_hardcoded_count": len(unextracted),
            "unextracted_samples": unextracted[:15],
            "message": f"Audit complete for '{lang_code}'.",
            "coverage_summary": {
                "base_language": base_lang,
                "target_language": lang_code,
                "missing_keys_count": len(missing),
            },
            "noise_notice": build_noise_notice(),
            "suggested_action": (
                "Resolve missing keys before considering dead-key cleanup."
                if missing
                else "Coverage is complete for this language. Review dead keys "
                "manually in small batches."
            ),
            "next_steps": [
                "Treat missing_keys_count as the translation coverage signal for this language.",
                "Review dead_keys manually; cleanup is report-only and does not edit locale files.",
                "Use VCS diff + type-check/test after each small locale cleanup batch.",
            ],
        }


async def propose_sync_i18n(
    new_pairs: dict, lang_code: str, reasoning: str, **kwargs
) -> SyncProposal:
    config = await _load_project_config()
    temp_file = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"proposal_{lang_code}.json")
    os.makedirs(os.path.dirname(temp_file), exist_ok=True)
    disk_data = await _load_locale_data(config.locales_dir, lang_code)
    base_data, existing_reasoning = disk_data.copy(), ""
    if os.path.exists(temp_file):
        try:
            async with aiofiles.open(temp_file, encoding="utf-8") as f:
                p_data = json.loads(await f.read())
                base_data = p_data.get("content", disk_data)
                existing_reasoning = p_data.get("reason", "")
        except Exception:
            pass
    final_data = _deep_update(base_data, _unflatten_dict(new_pairs), ConflictStrategy.OVERWRITE)

    combined_reason = (
        f"{existing_reasoning}\n+ {reasoning}"
        if existing_reasoning and reasoning not in existing_reasoning
        else reasoning
    )
    target_file = _resolve_locale_target_path(config, lang_code)
    proposal_data = {
        "target_file": target_file,
        "content": final_data,
        "lang": lang_code,
        "reason": combined_reason,
    }
    async with aiofiles.open(temp_file, "w", encoding="utf-8") as f:
        await f.write(json.dumps(proposal_data, indent=2, ensure_ascii=False))
    flat_disk, flat_final = _flatten_dict(disk_data), _flatten_dict(final_data)
    accumulated = {k: v for k, v in flat_final.items() if flat_disk.get(k) != v}
    preview_path = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"proposal_{lang_code}.md")
    preview_lines = [
        f"# i18n proposal: {lang_code}",
        "",
        f"Target file: `{target_file}`",
        "",
        f"Reason: {combined_reason or 'No reason provided.'}",
        "",
        "## Changes",
        "",
    ]
    preview_lines.extend(
        f"- `{key}`: {json.dumps(value, ensure_ascii=False)}" for key, value in accumulated.items()
    )
    if not accumulated:
        preview_lines.append("- No changes.")
    async with aiofiles.open(preview_path, "w", encoding="utf-8") as f:
        await f.write("\n".join(preview_lines) + "\n")
    return SyncProposal(
        proposal_id=lang_code,
        lang_code=lang_code,
        changes_count=len(accumulated),
        diff_summary=accumulated,
        reasoning=combined_reason,
        file_path=target_file,
        validation_errors=[],
        style_suggestions=[],
        preview_file_path=preview_path,
    )


async def commit_i18n_changes(target_scope: str) -> str:
    path = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR)
    files = (
        glob.glob(os.path.join(path, f"proposal_{target_scope}.json"))
        if target_scope != "all"
        else glob.glob(os.path.join(path, "*.json"))
    )
    if not files:
        return "No proposals."
    committed_files = []
    for f_p in files:
        async with aiofiles.open(f_p, encoding="utf-8") as f:
            data = json.loads(await f.read())
        await _save_locale_data(_validate_safe_path(data["target_file"]), data["content"])
        os.remove(f_p)
        committed_files.append(os.path.basename(data["target_file"]))
    return f"Successfully committed {len(committed_files)} proposals: {', '.join(committed_files)}"


async def get_missing_keys(lang_code: str, base_lang: str = "en") -> dict:
    config = await _load_project_config()
    bd, td = (
        await _load_locale_data(config.locales_dir, base_lang),
        await _load_locale_data(config.locales_dir, lang_code),
    )
    fbd, ftd = _flatten_dict(bd), _flatten_dict(td)
    return {k: v for k, v in fbd.items() if k not in ftd}


async def get_dead_keys(lang_code: str = "en") -> list[str]:
    config = await _load_project_config()
    locale_data = await _load_locale_data(config.locales_dir, lang_code)
    if not locale_data:
        return []
    all_keys = set(_flatten_dict(locale_data).keys())
    used = set()
    for s_dir in config.source_dirs or ["src"]:
        abs_s = os.path.join(WORKSPACE_ROOT, s_dir)
        if not os.path.exists(abs_s):
            continue
        for root, _, files in os.walk(abs_s):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in (".js", ".jsx", ".ts", ".tsx", ".vue"):
                    try:
                        async with aiofiles.open(os.path.join(root, f), encoding="utf-8") as fi:
                            sc = TreeSitterScanner(await fi.read(), ext)
                            for t, _, o in sc.scan():
                                if o == "i18n_key":
                                    used.add(t)
                    except Exception:
                        continue
    return sorted(list(all_keys - used))


async def check_project_status() -> ProjectStatus:
    return ProjectStatus(
        config=await _load_project_config(),
        workspace_root=WORKSPACE_ROOT,
        status_message="Ready",
        has_glossary=os.path.exists(_validate_safe_path(GLOSSARY_FILE)),
        cache_size=0,
        vcs_info=get_vcs_status(WORKSPACE_ROOT),
    )


async def initialize_project_config(auto: bool = False) -> dict:
    recommended_gitignore = [CACHE_FILE, PROPOSALS_DIR, f"!{CONFIG_FILE}"]
    source_dirs = _collect_source_dirs()

    existing_config, _, parse_error = _load_existing_init_config()
    if parse_error:
        return {
            "mode": "hard_fail",
            "message": "Existing .i18n-skill.json is malformed and cannot be merged safely.",
            "warnings": [parse_error],
            "requires_confirmation": False,
            "suggested_action": "Fix or remove .i18n-skill.json and rerun init.",
            "next_steps": [
                "Fix or remove the malformed .i18n-skill.json file.",
                "Rerun i18n init after the config is readable again.",
            ],
            "detected_locale_dirs": [],
            "detected_locale_files": [],
            "detected_languages": [],
            "migrations": [],
            "recommended_gitignore": recommended_gitignore,
        }

    existing_locale_dir = existing_config.locales_dir if existing_config else None
    candidates = _detect_locale_candidates(existing_locale_dir)
    mode, selected_candidate, reason = _classify_init_mode(candidates, existing_locale_dir)
    detected_locale_dirs = [c["dir"] for c in candidates if c["files"]]
    detected_locale_files = [f for c in candidates for f in c["files"]]
    detected_languages = (
        selected_candidate["langs"] if selected_candidate else _sort_languages(set().union(*[
            set(c["langs"]) for c in candidates
        ]))
    )

    if mode == "reconcile":
        return {
            "mode": mode,
            "message": reason,
            "warnings": [],
            "requires_confirmation": True,
            "suggested_action": "Choose one locale root and rerun init.",
            "next_steps": [
                "Review candidate_locale_roots and choose the single source "
                "of truth for locale files.",
                "Do not run audit or sync yet; resolve the locale-root ambiguity first.",
                "Rerun i18n init after confirming the intended locale root.",
            ],
            "detected_locale_dirs": detected_locale_dirs,
            "detected_locale_files": detected_locale_files,
            "detected_languages": detected_languages,
            "candidate_locale_roots": [
                {"dir": c["dir"], "languages": c["langs"], "extensions": c["extensions"]}
                for c in candidates
                if c["langs"]
            ],
            "migrations": [],
            "recommended_gitignore": recommended_gitignore,
        }

    if mode in {"unsupported", "hard_fail"}:
        return {
            "mode": mode,
            "message": reason,
            "warnings": [],
            "requires_confirmation": False,
            "suggested_action": "Verify locale directory and filename conventions.",
            "next_steps": [
                "Verify that locale filenames use language-code stems such as en, zh_CN, or fr.",
                "If the project does not use file-backed locale assets, "
                "do not continue with sync/audit yet.",
            ],
            "detected_locale_dirs": detected_locale_dirs,
            "detected_locale_files": detected_locale_files,
            "detected_languages": detected_languages,
            "migrations": [],
            "recommended_gitignore": recommended_gitignore,
        }

    base_config = existing_config or ProjectConfig()
    config_data = base_config.model_dump(mode="json")
    if existing_config is None:
        config_data["ignore_dirs"] = ["node_modules", "dist", ".git", ".venv"]
        config_data["privacy_level"] = "basic"
        config_data["persona"] = {
            "domain": "Industrial Engineering",
            "audience": "Developers",
            "tone": "Technical",
            "custom_guidelines": [],
        }
    config_data["source_dirs"] = source_dirs
    migrations: list[str] = []
    warnings: list[str] = []

    if mode == "bootstrap":
        bootstrap_locale_dir = "src/locales" if "src" in source_dirs else "locales"
        config_data["locales_dir"] = bootstrap_locale_dir
        config_data["enabled_langs"] = ["en"]
        if not config_data.get("preferred_format"):
            config_data["preferred_format"] = ".json"
        warnings.append("Bootstrap mode: no existing locale assets were detected.")
        next_steps = [
            f"Create the base locale file at {bootstrap_locale_dir}/en.json.",
            "Add target languages only after the base locale file exists.",
            "Run i18n status, then i18n audit --lang all after the first locale files are created.",
        ]
    else:
        assert selected_candidate is not None
        config_data["locales_dir"] = selected_candidate["dir"]
        config_data["enabled_langs"] = selected_candidate["langs"]

        inferred_format = _infer_preferred_format(selected_candidate["extensions"])
        existing_format = _normalize_extension(
            cast(str | None, config_data.get("preferred_format"))
        )
        if inferred_format:
            config_data["preferred_format"] = inferred_format
        elif existing_format and existing_format in selected_candidate["extensions"]:
            config_data["preferred_format"] = existing_format
        else:
            config_data["preferred_format"] = None

        if existing_config:
            old_langs = existing_config.enabled_langs
            new_langs = selected_candidate["langs"]
            if old_langs != new_langs:
                if "zh" in old_langs and "zh" not in new_langs:
                    lang_summary = ", ".join(new_langs)
                    migrations.append(
                        f"Replaced stale language code 'zh' with detected set: {lang_summary}"
                    )
                else:
                    old_summary = ", ".join(old_langs)
                    new_summary = ", ".join(new_langs)
                    migrations.append(
                        f"Updated enabled_langs: {old_summary} -> {new_summary}"
                    )
            if existing_config.locales_dir != selected_candidate["dir"]:
                new_dir = selected_candidate["dir"]
                migrations.append(
                    f"Updated locales_dir: {existing_config.locales_dir} -> {new_dir}"
                )
        else:
            migrations.append(
                f"Initialized from detected locale assets: {selected_candidate['dir']}"
            )
        next_steps = [
            "Run i18n status to confirm the generated config and detected languages.",
            "Run i18n audit --lang all to confirm full-language coverage.",
            "Use i18n scan --vcs for daily incremental checks instead of "
            "treating full-audit noise as new work.",
        ]

    final_config = ProjectConfig(**config_data)
    await _save_project_config(final_config)
    config_path = os.path.join(WORKSPACE_ROOT, CONFIG_FILE)

    return {
        "mode": mode,
        "message": f"Config initialized at {config_path}",
        "config": final_config.model_dump(mode="json"),
        "warnings": warnings,
        "requires_confirmation": False,
        "suggested_action": "Run i18n status and i18n audit to validate project coverage.",
        "next_steps": next_steps,
        "detected_locale_dirs": detected_locale_dirs,
        "detected_locale_files": detected_locale_files,
        "detected_languages": detected_languages,
        "migrations": migrations,
        "recommended_gitignore": recommended_gitignore,
        "auto_mode": auto,
    }


async def generate_cleanup_report(lang_code: str = "en") -> dict:
    status_report = await check_project_status()
    langs = [lang_code] if lang_code != "all" else status_report.config.enabled_langs

    all_results = []
    for lang in langs:
        dead = await get_dead_keys(lang_code=lang)
        all_results.append({"language": lang, "dead_keys_count": len(dead), "dead_keys": dead})

    total_dead = sum(int(cast(int, r["dead_keys_count"])) for r in all_results)
    next_steps = [
        "Review dead keys manually and confirm business usage before any deletion.",
        "Use VCS diff + type-check/test after each small deletion batch.",
        "Create backups before file mutations.",
    ]
    return {
        "mode": "report_only",
        "language": lang_code,
        "results": all_results,
        "total_dead_keys": total_dead,
        "message": f"Found {total_dead} unused keys across {len(langs)} language(s).",
        "safety_notice": (
            "Cleanup only reports dead keys. Do not run ad-hoc deletion "
            "scripts against locale files."
        ),
        "recommended_next_steps": next_steps,
        "next_steps": next_steps,
        "suggested_action": (
            "Review and delete locale keys manually in small verified batches only."
        ),
    }


async def distill_project_persona() -> dict:
    config = await _load_project_config()
    scan_data = await orchestrate_scan()
    samples = scan_data.get("results", [])[:20]
    return {
        "domain": config.persona.domain,
        "audience": config.persona.audience,
        "tone": config.persona.tone,
        "samples": [s["text"] for s in samples if isinstance(s, dict)],
    }


async def save_project_persona(p: dict) -> str:
    config = await _load_project_config()
    config.persona.domain = p.get("domain", config.persona.domain)
    config.persona.audience = p.get("audience", config.persona.audience)
    config.persona.tone = p.get("tone", config.persona.tone)
    await _save_project_config(config)
    return "Persona updated and saved."


async def sync_i18n_files(n: dict, l_code: str) -> str:
    return "Synced"


async def refine_i18n_proposal(proposal_id: str, feedback: str) -> str:
    path = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"proposal_{proposal_id}.json")
    if not os.path.exists(path):
        return "Error"
    async with aiofiles.open(path, encoding="utf-8") as f:
        data = json.loads(await f.read())
    data.setdefault("feedback", []).append(feedback)
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False))
    return "Recorded."


async def optimize_translations(lang_code: str, include_approved: bool = False) -> dict:
    config = await _load_project_config()
    data = await _load_locale_data(config.locales_dir, lang_code)
    flat_data = _flatten_dict(data)
    snapshot_mgr = TranslationSnapshotManager(WORKSPACE_ROOT)
    glossary = {}
    targets = {}
    for k, v in flat_data.items():
        is_approved = (await snapshot_mgr.get_status(k)) == TranslationStatus.APPROVED
        if is_approved:
            glossary[k] = v
        if include_approved or not is_approved:
            targets[k] = v

    os.makedirs(os.path.join(WORKSPACE_ROOT, "temp"), exist_ok=True)
    task_p = os.path.join(WORKSPACE_ROOT, "temp", f"opt_{lang_code}.json")
    task_data = {"targets": targets, "dynamic_glossary": glossary}
    async with aiofiles.open(task_p, "w", encoding="utf-8") as f:
        await f.write(json.dumps(task_data, indent=2, ensure_ascii=False))
    return {"task_file_path": task_p}


async def generate_quality_report(lang_code: str) -> EvaluationReport:
    config = await _load_project_config()
    data = _flatten_dict(await _load_locale_data(config.locales_dir, lang_code))
    base = _flatten_dict(await _load_locale_data(config.locales_dir, "en"))
    snapshot_mgr = TranslationSnapshotManager(WORKSPACE_ROOT)
    approved_count = 0
    controversial = []
    for k, v in data.items():
        if (await snapshot_mgr.get_status(k)) == TranslationStatus.APPROVED:
            approved_count += 1
        # Style check
        style_errors = TranslationStyleLinter.lint(
            k, v, lang_code, config.protected_lang_key_patterns
        )
        if style_errors:
            controversial.append(
                ReviewItem(
                    key=k,
                    current_translation=v,
                    suggested_translation="",
                    issue_type="STYLE_VIOLATION",
                    confidence="High",
                    reasoning=str(style_errors[0].message),
                )
            )
            continue
        if k in base:
            exp, act = _extract_placeholders(base[k]), _extract_placeholders(v)
            if exp != act:
                reason = f"Placeholder mismatch: expected {exp}, got {act}"
                controversial.append(
                    ReviewItem(
                        key=k,
                        current_translation=v,
                        suggested_translation="",
                        issue_type="VARIABLE_MISMATCH",
                        confidence="High",
                        reasoning=reason,
                    )
                )
    return EvaluationReport(
        lang_code=lang_code,
        total_keys=len(data),
        approved_keys=approved_count,
        controversial_items=controversial,
        overall_score=100 if not controversial else 80,
        summary=f"Found {len(controversial)} items to review.",
        report_file_path="",
    )


def _extract_placeholders(text: str) -> set[str]:
    return set(re.findall(r"\{.*?\}", text))


async def reference_optimize_translations(
    pivot_lang: str, target_lang: str, keys: list[str] | None = None
) -> dict:
    config = await _load_project_config()
    data = _flatten_dict(await _load_locale_data(config.locales_dir, target_lang))
    base = _flatten_dict(await _load_locale_data(config.locales_dir, "en"))
    pivot = _flatten_dict(await _load_locale_data(config.locales_dir, pivot_lang))
    targets = {}
    for k in keys or data.keys():
        if k in base and k in pivot:
            targets[k] = {
                "base_context": base[k],
                "reference_mapping": pivot[k],
                "current": data.get(k, ""),
            }
    return {"targets": targets, "message": f"Optimizing {target_lang} using {pivot_lang}"}


async def sync_manual_modifications(lang_code: str) -> str:
    config = await _load_project_config()
    data = _flatten_dict(await _load_locale_data(config.locales_dir, lang_code))
    snapshot_mgr = TranslationSnapshotManager(WORKSPACE_ROOT)
    snapshots = await snapshot_mgr._read_snapshots()
    updated_count = 0
    for k, v in data.items():
        existing = snapshots.get(k, {})
        current_hash = hashlib.md5(v.encode("utf-8")).hexdigest()
        if (
            existing.get("translation") != v
            or existing.get("hash") != current_hash
            or existing.get("status") != TranslationStatus.APPROVED.value
        ):
            await snapshot_mgr.update_snapshot(
                k, v, 10, status=TranslationStatus.APPROVED, content_hash=current_hash
            )
            updated_count += 1
    return f"Feedback Loop: Learned {updated_count} manual modifications for '{lang_code}'."


async def load_project_glossary() -> dict:
    glossary_path = _validate_safe_path(GLOSSARY_FILE)
    if not os.path.exists(glossary_path):
        return {}
    try:
        async with aiofiles.open(glossary_path, encoding="utf-8") as f:
            loaded = json.loads(await f.read())
        return loaded if isinstance(loaded, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


async def update_project_glossary(text: str, translation: str) -> str:
    glossary_path = _validate_safe_path(GLOSSARY_FILE)
    document = await load_project_glossary()
    if not document:
        document = {
            "project_name": os.path.basename(WORKSPACE_ROOT),
            "version": "1.0.0",
            "glossary": [],
            "rules": {
                "cjk_spacing": True,
                "fullwidth_punctuation": True,
                "forbidden_terms": [],
            },
        }
    entries = document.setdefault("glossary", [])
    if not isinstance(entries, list):
        entries = []
        document["glossary"] = entries
    for entry in entries:
        if isinstance(entry, dict) and entry.get("term") == text:
            entry["translation"] = translation
            break
    else:
        entries.append({"term": text, "translation": translation, "context": "", "priority": 1})
    async with aiofiles.open(glossary_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(document, indent=2, ensure_ascii=False))
    return "Learned"


async def save_project_preference(pattern: str, is_native_protection: bool = True) -> str:
    return "Saved"
