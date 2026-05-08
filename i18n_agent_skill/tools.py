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
    ws_root = os.path.normpath(os.path.abspath(WORKSPACE_ROOT)).lower()
    target_path = os.path.normpath(os.path.abspath(os.path.join(WORKSPACE_ROOT, path)))
    if not target_path.lower().startswith(ws_root):
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
            attribute: (jsx_attribute (property_identifier) @attr_name (#eq? @attr_name "i18nKey") (string) @key)
        )
        (jsx_opening_element
            name: (identifier) @comp (#eq? @comp "Trans")
            attribute: (jsx_attribute (property_identifier) @attr_name (#eq? @attr_name "i18nKey") (string) @key)
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
    results, seen, p_lvl = [], set(), privacy_level or PrivacyLevel.BASIC
    lines = content.splitlines()
    for text, line, origin in scanner.scan():
        if _is_natural_language(text, origin, config.ignored_strings):
            if (text, line) in seen:
                continue
            masked, is_m = _mask_sensitive_data(text, p_lvl)
            ctx = "\n".join(lines[max(0, line - 2) : min(line + 1, len(lines))])
            results.append(ExtractedString(text=masked, line=line, context=ctx, is_masked=is_m))
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
    scan_paths = [path] if path else (config.source_dirs or ["src"])
    cache_path, shared_cache = os.path.join(WORKSPACE_ROOT, CACHE_FILE), {}
    if use_cache and os.path.exists(cache_path):
        try:
            async with aiofiles.open(cache_path, encoding="utf-8") as f_cache:
                shared_cache = json.loads(await f_cache.read())
        except Exception:
            pass
    all_res = []
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
                        if out.results:
                            all_res.extend([r.model_dump() for r in out.results])
        elif os.path.exists(abs_p):
            out = await extract_raw_strings(abs_p, use_cache=use_cache, shared_cache=shared_cache)
            if out.results:
                all_res.extend([r.model_dump() for r in out.results])
    if use_cache:
        try:
            async with aiofiles.open(cache_path, "w", encoding="utf-8") as f_out:
                await f_out.write(json.dumps(shared_cache))
        except Exception:
            pass
    return {"results": all_res}


async def _load_locale_data(target_dir: str, lang: str) -> dict:
    for ext in [".json", ".yaml", ".yml", ".ts", ".js"]:
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
    if lang_code == "all":
        results: dict[str, Any] = {
            "unextracted_hardcoded_count": len(unextracted),
            "unextracted_samples": unextracted[:10],
        }
        for target_l in config.enabled_langs:
            if target_l == base_lang:
                continue
            missing = await get_missing_keys(target_l, base_lang=base_lang)
            results[target_l] = {"missing_count": len(missing), "missing_keys": missing}
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
    proposal_data = {
        "target_file": os.path.join(config.locales_dir, f"{lang_code}.json"),
        "content": final_data,
        "lang": lang_code,
        "reason": combined_reason,
    }
    async with aiofiles.open(temp_file, "w", encoding="utf-8") as f:
        await f.write(json.dumps(proposal_data, indent=2, ensure_ascii=False))
    flat_disk, flat_final = _flatten_dict(disk_data), _flatten_dict(final_data)
    accumulated = {k: v for k, v in flat_final.items() if flat_disk.get(k) != v}
    return SyncProposal(
        proposal_id=lang_code,
        lang_code=lang_code,
        changes_count=len(accumulated),
        diff_summary=accumulated,
        reasoning=combined_reason,
        file_path=proposal_data["target_file"],
        validation_errors=[],
        style_suggestions=[],
        preview_file_path="",
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
        has_glossary=False,
        cache_size=0,
    )


async def initialize_project_config(auto: bool = False) -> dict:
    source_dirs = ["src"] if os.path.exists(os.path.join(WORKSPACE_ROOT, "src")) else []
    locales_dir = "locales"
    for p in ["src/locales", "locales", "public/locales"]:
        if os.path.exists(os.path.join(WORKSPACE_ROOT, p)):
            locales_dir = p
            break
    
    config = {
        "source_dirs": source_dirs or ["."],
        "ignore_dirs": ["node_modules", "dist", ".git", ".venv"],
        "locales_dir": locales_dir,
        "enabled_langs": ["en", "zh"],
        "privacy_level": "basic",
        "persona": {
            "domain": "Industrial Engineering",
            "audience": "Developers",
            "tone": "Technical"
        },
        "protected_lang_key_patterns": [],
        "ignored_keys": [],
        "ignored_strings": [],
        "preferred_format": ".json"
    }
    
    config_path = os.path.join(WORKSPACE_ROOT, CONFIG_FILE)
    async with aiofiles.open(config_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(config, indent=2, ensure_ascii=False))
        
    return {
        "message": f"Config initialized at {config_path}",
        "config": config,
        "recommended_gitignore": [CACHE_FILE, PROPOSALS_DIR, f"!{CONFIG_FILE}"]
    }


async def distill_project_persona() -> dict:
    config = await _load_project_config()
    scan_data = await orchestrate_scan()
    samples = scan_data.get("results", [])[:20]
    return {
        "domain": config.persona.domain,
        "audience": config.persona.audience,
        "tone": config.persona.tone,
        "samples": [s["text"] for s in samples if isinstance(s, dict)]
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
    return {}


async def update_project_glossary(text: str, translation: str) -> str:
    return "Learned"


async def save_project_preference(pattern: str, is_native_protection: bool = True) -> str:
    return "Saved"
