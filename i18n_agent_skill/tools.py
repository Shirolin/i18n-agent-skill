import asyncio
import glob
import hashlib
import json
import os
import re
import subprocess
import time
from typing import Any, cast

import aiofiles
import yaml

from i18n_agent_skill import vcs

# Core dependencies: Tree-sitter lexical analysis suite
try:
    # Enforce version check
    import importlib.metadata

    import tree_sitter
    import tree_sitter_language_pack
    from tree_sitter import Language, Parser

    ts_version = importlib.metadata.version("tree-sitter")

    # Use simple tuple comparison to avoid 'packaging' dependency
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

from i18n_agent_skill.linter import TranslationStyleLinter
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
    ValidationFeedback,
)
from i18n_agent_skill.snapshot import TranslationSnapshotManager

# Global Constants
CACHE_FILE = ".i18n-cache.json"
PROPOSALS_DIR = ".i18n-proposals"
GLOSSARY_FILE = "GLOSSARY.json"
CONFIG_FILE = ".i18n-skill.json"


def _is_skill_source_dir(directory: str) -> bool:
    """[Defensive] Check if the directory contains the source code of this tool itself."""
    skill_md = os.path.join(directory, "SKILL.md")
    pyproject = os.path.join(directory, "pyproject.toml")
    try:
        if os.path.exists(skill_md):
            with open(skill_md, encoding="utf-8") as f:
                if "name: i18n-agent-skill" in f.read():
                    return True
        if os.path.exists(pyproject):
            with open(pyproject, encoding="utf-8") as f:
                if 'name = "i18n-agent-skill"' in f.read():
                    return True
    except Exception:
        pass
    return False


def _resolve_workspace_root(explicit_root: str | None = None) -> str:
    """Dynamically resolve project root based on file markers."""
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


def set_workspace_root(path: str | None = None):
    global WORKSPACE_ROOT
    WORKSPACE_ROOT = _resolve_workspace_root(path)


# Sensitive Information Defense Matrix
SENSITIVE_PATTERNS = {
    "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "API_KEY": r"(?:sk-[a-zA-Z0-9-]{20,}|AKIA[a-zA-Z0-9]{16}|[a-zA-Z0-9]{32,})",
    "IP_ADDR": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    "PHONE": r"(?:\+|00)?[1-9]\d{6,14}|1[3-9]\d{9}|(?:0\d{2,3}-)?\d{7,8}",
    "ID_CARD": r"[1-9]\d{16}[0-9Xx]",
}

UI_ATTRS = {"placeholder", "title", "label", "aria-label", "alt", "value"}


def _flatten_dict(d: dict, p_key: str = "", sep: str = ".") -> dict:
    """Flatten nested JSON into dot-separated key-value pairs."""
    items: list[tuple[str, str]] = []
    for k, v in d.items():
        new_key = f"{p_key}{sep}{k}" if p_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, str(v)))
    return dict(items)


def _unflatten_dict(d: dict, sep: str = ".") -> dict:
    """Restore dot-separated key-value pairs into nested JSON."""
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
    """Deep merge nested dictionaries following specified conflict strategy."""
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            _deep_update(d[k], v, strategy)
        else:
            if k in d and strategy == ConflictStrategy.KEEP_EXISTING:
                continue
            d[k] = v
    return d


def _mask_sensitive_data(text: str, level: PrivacyLevel) -> tuple[str, bool]:
    """Heuristic Privacy Masking Engine."""
    lvl_str = str(level.value if hasattr(level, "value") else level).lower()
    if lvl_str == "off":
        return text, False

    masked_text, is_masked = text, False
    if lvl_str == "basic":
        patterns_to_check = ["EMAIL", "API_KEY"]
    else:
        # STRICT mode includes PHONE, ID_CARD, IP_ADDR, etc.
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
    """Strict Sandbox Validation."""
    ws_root = os.path.normpath(os.path.abspath(WORKSPACE_ROOT)).lower()
    target_path = os.path.normpath(os.path.abspath(os.path.join(WORKSPACE_ROOT, path)))
    if not target_path.lower().startswith(ws_root):
        raise PermissionError(f"Access Denied: Path '{path}' is outside project.")
    return target_path


def _is_natural_language(text: str, origin: str) -> bool:
    """Globalization eligibility determination with high-fidelity noise filtering."""
    if origin == "fallback_text":
        return False # Fallback text in {t('key') || 'fallback'} is already 'handled'
        
    t = text.strip()
    # Skip very short strings or technical constants
    if len(t) < 2 or re.match(r"^[a-z0-9._\-\[\]]+$", t, re.IGNORECASE):
        if not re.search(r"[^\x00-\x7f]", t): # Unless it contains non-ASCII
            return False

    # Skip common code patterns that look like text but aren't UI
    technical_prefixes = ("http", "env:", "calc(", "var(", "--", "@", "./", "../")
    if t.lower().startswith(technical_prefixes):
        return False

    # Privacy Shield: Detect sensitive data patterns
    for pattern in SENSITIVE_PATTERNS.values():
        if re.search(pattern, t, re.IGNORECASE):
            return True

    # Non-ASCII is almost always UI text (Chinese, Japanese, etc.)
    if re.search(r"[^\x00-\x7f]", t):
        return True

    # Code vs Text-node logic
    if origin == "text_node":
        return True
    
    # Heuristics for English UI text: contains spaces or ending punctuation
    return bool(" " in t or re.search(r"[.!?:]$", t))


QUERY_STRINGS = {
    "jsx": """
        (jsx_text) @text
        (string) @str
        (template_string) @str
        (import_statement) @skip
        (call_expression 
            function: [
                (identifier) @func (#any-of? @func "t" "$t")
                (member_expression property: (property_identifier) @method (#eq? @method "t"))
            ]
            arguments: (arguments . (string) @key)
        )
        (binary_expression
            left: (call_expression 
                function: [
                    (identifier) @func (#any-of? @func "t" "$t")
                    (member_expression property: (property_identifier) @method (#eq? @method "t"))
                ]
            )
            right: [
                (string) @fallback
                (template_string) @fallback
            ]
        )
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
        (string) @str
        (template_string) @str
        (import_statement) @skip
        (call_expression 
            function: [
                (identifier) @func (#any-of? @func "t" "$t")
                (member_expression property: (property_identifier) @method (#eq? @method "t"))
            ]
            arguments: (arguments . (string) @key)
        )
        (binary_expression
            left: (call_expression 
                function: [
                    (identifier) @func (#any-of? @func "t" "$t")
                    (member_expression property: (property_identifier) @method (#eq? @method "t"))
                ]
            )
            right: [
                (string) @fallback
                (template_string) @fallback
            ]
        )
    """,
}


class TreeSitterScanner:
    """Tree-sitter based pixel-perfect scanning engine."""

    def __init__(self, content: str, file_ext: str):
        self.content_bytes = content.encode("utf-8")
        self.file_ext = file_ext

    def _get_lang(self, lang_name: str) -> Language | None:
        """Modern language loader: use language_pack for full support."""
        try:
            return tree_sitter_language_pack.get_language(lang_name)  # type: ignore
        except Exception:
            return None

    def _get_lang_keys(self, ext: str) -> tuple[str, str]:
        if ext in (".jsx", ".tsx"):
            return "tsx", "jsx"
        if ext == ".vue":
            return "vue", "vue"
        return "javascript", "js"

    def scan(
        self, c_bytes: bytes | None = None, ext: str | None = None, line_offset: int = 0
    ) -> list[tuple[str, int, str]]:
        if not DEPENDENCIES_INSTALLED:
            return []
        target_bytes = c_bytes or self.content_bytes
        target_ext = ext or self.file_ext
        l_key, q_key = self._get_lang_keys(target_ext)

        lang = self._get_lang(l_key)
        if not lang:
            return []

        try:
            parser = Parser(lang)
            tree = parser.parse(target_bytes)
            query_str = QUERY_STRINGS.get(q_key, QUERY_STRINGS["js"])
            query = tree_sitter.Query(lang, query_str)
            cursor = tree_sitter.QueryCursor(query)
            matches = cursor.matches(tree.root_node)

            res = []
            skip_nodes = set()
            fallback_nodes = set()

            # Pre-pass to identify nodes to skip or treat as fallback
            for _, captures in matches:
                if "skip" in captures:
                    for node in captures["skip"]:
                        skip_nodes.add(node.id)
                if "fallback" in captures:
                    for node in captures["fallback"]:
                        fallback_nodes.add(node.id)

            processed_node_ids = set()

            for _, captures in matches:
                # Priority 0: Skip logic
                if "skip" in captures:
                    continue

                # Priority 1: Check for i18n keys (@key)
                if "key" in captures:
                    for node in captures["key"]:
                        if node.id in processed_node_ids:
                            continue
                        try:
                            key_text = node.text.decode("utf-8").strip("'\"")
                            line_no = node.start_point[0] + 1 + line_offset
                            res.append((key_text, line_no, "i18n_key"))
                            processed_node_ids.add(node.id)
                        except Exception:
                            continue
                    continue

                # Priority 2: Check for natural language text (@text, @script, @fallback, @str)
                for c_name, nodes in captures.items():
                    if c_name in ("attr_name", "func", "method"):
                        continue

                    for node in nodes:
                        if node.id in processed_node_ids:
                            continue
                            
                        # Improved skipping: check if current node or any ancestor is in skip_nodes
                        curr_n = node
                        is_skipped = False
                        while curr_n:
                            if curr_n.id in skip_nodes:
                                is_skipped = True
                                break
                            curr_n = curr_n.parent
                        
                        if is_skipped:
                            continue
                        
                        try:
                            t_bytes: Any = target_bytes[node.start_byte : node.end_byte]
                            text = t_bytes.decode("utf-8")
                        except Exception:
                            continue

                        line_no = node.start_point[0] + 1 + line_offset
                        if c_name == "script":
                            res.extend(self.scan(t_bytes, ".js", line_offset=line_no - 1))
                            processed_node_ids.add(node.id)
                            continue

                        if node.type in ("string", "template_string"):
                            text = re.sub(r'^["\'`]|["\'`]$', "", text)
                            if node.type == "template_string":
                                text = re.sub(r"\$\{.*?\}", "{var}", text)

                        origin = "code"
                        if c_name == "text" or node.type == "jsx_text":
                            origin = "text_node"
                        elif c_name == "fallback" or node.id in fallback_nodes:
                            origin = "fallback_text"

                        res.append((text, line_no, origin))
                        processed_node_ids.add(node.id)

            return res
        except Exception as e:
            logger.error(f"AST Scan Error: {str(e)}")
            return []


# Duplicate _is_natural_language removed during refactor


async def extract_raw_strings(
    file_path: str,
    use_cache: bool = True,
    vcs_mode: bool = False,
    privacy_level: PrivacyLevel | None = None,
    shared_cache: dict[str, Any] | None = None,
) -> ExtractOutput:
    """Strict AST scanning, no RegEx fallback."""
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
                suggested_action="Run the bootstrap installer to fix environment.",
                executable_hint="./install.sh",
            )
        )

    start_ts = time.perf_counter()
    if not os.path.exists(safe_p):
        return ExtractOutput(
            error=ErrorInfo(
                error_code="PATH_ERR",
                message=f"File not found: {file_path}",
                suggested_action="Verify the file path exists within your workspace.",
            )
        )

    async with aiofiles.open(safe_p, encoding="utf-8") as f:
        content = await f.read()
    ext = os.path.splitext(file_path)[1].lower()

    content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
    if use_cache and shared_cache is not None:
        if safe_p in shared_cache and shared_cache[safe_p]["hash"] == content_hash:
            return ExtractOutput(
                results=[ExtractedString(**r) for r in shared_cache[safe_p]["results"]],
                is_cached=True,
                telemetry=TelemetryData(
                    duration_ms=0,
                    files_processed=1,
                    cache_hits=1,
                    keys_extracted=len(shared_cache[safe_p]["results"]),
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

    if use_cache and shared_cache is not None:
        shared_cache[safe_p] = {"hash": content_hash, "results": [r.model_dump() for r in results]}

    duration = (time.perf_counter() - start_ts) * 1000
    telemetry = TelemetryData(
        duration_ms=duration,
        files_processed=1,
        keys_extracted=len(results),
        privacy_shield_hits=privacy_hits,
    )
    return ExtractOutput(results=results, telemetry=telemetry)


async def orchestrate_scan(
    path: str | None = None, use_cache: bool = True, vcs_mode: bool = False
) -> dict[str, Any]:
    """[Orchestration] Scan multiple paths or directories and aggregate results."""
    config = await _load_project_config()
    scan_paths = [path] if path else (config.source_dirs or ["src"])

    all_results = []
    total_tel = {
        "duration_ms": 0.0,
        "files_processed": 0,
        "keys_extracted": 0,
        "privacy_shield_hits": 0,
    }
    valid_exts = {".js", ".jsx", ".ts", ".tsx", ".vue"}

    # Optimization: Pre-load cache once to avoid O(N^2) I/O
    cache_path = os.path.join(WORKSPACE_ROOT, CACHE_FILE)
    shared_cache = {}
    if use_cache and os.path.exists(cache_path):
        try:
            async with aiofiles.open(cache_path, encoding="utf-8") as f:
                shared_cache = json.loads(await f.read())
        except Exception:
            pass

    # VCS Mode optimization: only scan changed files
    changed_files = set()
    if vcs_mode:
        v_status = vcs.get_vcs_status(WORKSPACE_ROOT)
        if v_status and v_status.get("is_dirty"):
            # We use git diff --name-only internally in get_vcs_status if I added it,
            # let's double check vcs.py or just run it here.
            # Actually, I should probably expose a get_changed_files in vcs.py.
            # For now, let's just get it here for simplicity or update vcs.py.
            try:
                res = subprocess.run(
                    ["git", "diff", "--name-only"],
                    cwd=WORKSPACE_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res.returncode == 0:
                    changed_files = {
                        os.path.normpath(os.path.join(WORKSPACE_ROOT, f)).lower()
                        for f in res.stdout.strip().split("\n")
                        if f.strip()
                    }
            except Exception:
                pass

    tasks = []
    for p in scan_paths:
        abs_p = (
            os.path.normpath(os.path.join(WORKSPACE_ROOT, p))
            if not os.path.isabs(p)
            else os.path.normpath(p)
        )
        if os.path.isdir(abs_p):
            for root, _, files in os.walk(abs_p):
                # Skip ignore_dirs
                if any(
                    ignored in root.replace("\\", "/").split("/") for ignored in config.ignore_dirs
                ):
                    continue
                for file in files:
                    if os.path.splitext(file)[1].lower() in valid_exts:
                        fpath = os.path.normpath(os.path.join(root, file))
                        if vcs_mode and fpath.lower() not in changed_files:
                            continue
                        tasks.append(
                            extract_raw_strings(
                                fpath,
                                use_cache=use_cache,
                                vcs_mode=vcs_mode,
                                shared_cache=shared_cache,
                            )
                        )
        elif os.path.exists(abs_p):
            fpath = os.path.normpath(abs_p)
            if vcs_mode and fpath.lower() not in changed_files:
                continue
            tasks.append(
                extract_raw_strings(
                    fpath, use_cache=use_cache, vcs_mode=vcs_mode, shared_cache=shared_cache
                )
            )

    # Execution Phase: Concurrent scanning
    scan_results = await asyncio.gather(*tasks)

    for res in scan_results:
        if res.results:
            all_results.extend([r.model_dump() for r in res.results])
        if res.telemetry:
            total_tel["duration_ms"] += res.telemetry.duration_ms
            total_tel["files_processed"] += res.telemetry.files_processed
            total_tel["keys_extracted"] += res.telemetry.keys_extracted
            total_tel["privacy_shield_hits"] += getattr(res.telemetry, "privacy_shield_hits", 0)

    # Optimization: Write back cache once
    if use_cache and tasks:
        try:
            async with aiofiles.open(cache_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(shared_cache))
        except Exception:
            pass

    return {"results": all_results, "telemetry": total_tel}


async def orchestrate_audit(lang_code: str = "all", base_lang: str = "en") -> dict[str, Any]:
    """[Orchestration] Perform multi-language or single-language audit with dead-key detection."""
    config = await _load_project_config()
    target_dir = _detect_locale_dir(config)
    abs_target_dir = os.path.join(WORKSPACE_ROOT, target_dir)

    # 0. Format Collision Detection
    warnings = []
    if os.path.exists(abs_target_dir):
        files = os.listdir(abs_target_dir)
        lang_formats: dict[str, list[str]] = {}
        for f in files:
            m = re.match(r"^([a-zA-Z0-9_-]+)\.(json|ts|js|yaml|yml)$", f)
            if m:
                l, ext = m.group(1), m.group(2)
                if l not in ("index", "types"):
                    lang_formats.setdefault(l, []).append(ext)
        
        for l, formats in lang_formats.items():
            if len(formats) > 1:
                warnings.append(
                    f"Format Collision: '{l}' has multiple files: {formats}. "
                    "This may cause inconsistent results."
                )

    if lang_code != "all" and lang_code not in config.enabled_langs:
        return {
            "error": (
                f"Language '{lang_code}' is not enabled. Use 'init' or update .i18n-skill.json."
            ),
            "warnings": warnings
        }

    # 1. Background Silent Scan (Difference-Driven)
    # We scan once to find all hardcoded strings in the project
    scan_data = await orchestrate_scan(use_cache=True)
    raw_strings = scan_data.get("results", [])
    
    # Load base locale to filter out already extracted strings
    base_data = _flatten_dict(await _load_locale_data(target_dir, base_lang))
    
    unextracted = []
    seen_texts = set()
    for s in raw_strings:
        txt = s.get("text", "")
        if txt not in base_data.values() and txt not in seen_texts:
            unextracted.append(s)
            seen_texts.add(txt)

    if lang_code == "all":
        results: dict[str, Any] = {"unextracted_hardcoded_count": len(unextracted), "warnings": warnings}
        if unextracted:
            results["unextracted_samples"] = unextracted[:10]

        for target_l in config.enabled_langs:
            if target_l == base_lang:
                continue
            missing_keys = await get_missing_keys(target_l, base_lang=base_lang)
            results[target_l] = {
                "missing_count": len(missing_keys),
                "missing_keys": missing_keys,
            }
        return results
    else:
        missing_keys = await get_missing_keys(lang_code, base_lang=base_lang)
        dead_keys = await get_dead_keys(lang_code=lang_code)
        
        return {
            "language": lang_code,
            "missing_keys_count": len(missing_keys),
            "missing_keys": missing_keys,
            "dead_keys_count": len(dead_keys),
            "dead_keys": dead_keys,
            "unextracted_hardcoded_count": len(unextracted),
            "unextracted_samples": unextracted[:15],
            "warnings": warnings,
            "message": (
                f"Audit complete for '{lang_code}'. "
                f"Found {len(missing_keys)} missing keys, {len(dead_keys)} unused keys, "
                f"and {len(unextracted)} un-extracted hardcoded strings."
            ),
        }


def _extract_placeholders(text: str) -> set[str]:
    """Extract variable placeholders like {name} or {{count}}."""
    return set(re.findall(r"\{\{.*?\}\}|\{.*?\}", text))


def _is_chrome_format(data: dict) -> bool:
    """Detect if data follows Chrome i18n format (keys mapping to objects with 'message')."""
    if not data:
        return False
    # Sample check
    sample_keys = list(data.keys())[:10]
    wrapped_count = 0
    for k in sample_keys:
        v = data[k]
        if isinstance(v, dict) and "message" in v:
            wrapped_count += 1
    return wrapped_count > len(sample_keys) / 2


def _smart_merge_i18n(base: dict, updates: dict) -> dict:
    """Merge flat updates into a possibly nested base, respecting Chrome format."""
    is_chrome = _is_chrome_format(base)
    flat_base = _flatten_dict(base)

    for k, v in updates.items():
        # Case 1: Target key already exists in flat base (update mode)
        if k in flat_base:
            flat_base[k] = v
        # Case 2: New key in a Chrome-formatted project
        elif is_chrome and not k.endswith(".message"):
            flat_base[f"{k}.message"] = v
        # Case 3: Regular new key
        else:
            flat_base[k] = v

    return _unflatten_dict(flat_base)


async def propose_sync_i18n(
    new_pairs: dict, lang_code: str, reasoning: str, **kwargs
) -> SyncProposal:
    """Generate a synchronization proposal with placeholder validation."""
    config = await _load_project_config()
    target_dir = _detect_locale_dir(config)

    file_p = _validate_safe_path(os.path.join(target_dir, f"{lang_code}.json"))
    base_p = _validate_safe_path(os.path.join(target_dir, "en.json"))

    base_d, val_errs, style_feedbacks = {}, [], []

    try:
        if os.path.exists(base_p):
            async with aiofiles.open(base_p, encoding="utf-8") as f:
                base_d = _flatten_dict(json.loads(await f.read()))
    except Exception:
        pass

    for k, v in new_pairs.items():
        # Validate against flattened base
        check_key = f"{k}.message" if f"{k}.message" in base_d else k
        if check_key in base_d:
            exp = _extract_placeholders(base_d[check_key])
            act = _extract_placeholders(v)
            if exp != act:
                val_errs.append(
                    ValidationFeedback(
                        key=k,
                        expected_placeholders=list(exp),
                        actual_placeholders=list(act),
                        message="Variable placeholders mismatch.",
                    )
                )

        style_feedbacks.extend(
            TranslationStyleLinter.lint(k, v, lang_code, config.protected_lang_key_patterns)
        )

    disk_data = await _load_locale_data(target_dir, lang_code)
    temp_file = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"proposal_{lang_code}.json")
    os.makedirs(os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR), exist_ok=True)

    # Use smart merge to preserve structure
    final_data = _smart_merge_i18n(disk_data, new_pairs)

    existing_reasoning = ""
    if os.path.exists(temp_file):
        try:
            with open(temp_file, encoding="utf-8") as f:
                p_data = json.load(f)
                # If existing proposal exists, merge new updates into it
                merged_content = _smart_merge_i18n(p_data.get("content", {}), new_pairs)
                final_data = merged_content
                existing_reasoning = p_data.get("reason", "")
        except Exception:
            pass

    if existing_reasoning and reasoning not in existing_reasoning:
        combined_reason = f"{existing_reasoning}\n+ {reasoning}"
    else:
        combined_reason = reasoning

    proposal_data = {
        "target_file": file_p,
        "content": final_data,
        "lang": lang_code,
        "reason": combined_reason,
    }
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(proposal_data, f, indent=2, ensure_ascii=False)

    flat_disk = _flatten_dict(disk_data)
    flat_final = _flatten_dict(final_data)
    accumulated_changes = {k: v for k, v in flat_final.items() if flat_disk.get(k) != v}

    preview_file = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"sync_preview_{lang_code}.md")
    with open(preview_file, "w", encoding="utf-8") as f:
        f.write(f"# i18n Sync Preview ({lang_code})\n\n")
        f.write(
            "Please review the changes in the **Staging Area**. "
            "When ready, run `commit` to apply.\n\n"
        )
        f.write(f"- **Language**: `{lang_code}`\n")
        f.write(f"- **Target File**: `{file_p}`\n")
        f.write(f"- **Accumulated Changes**: {len(accumulated_changes)}\n")
        f.write(f"- **Reasoning History**:\n```text\n{combined_reason}\n```\n\n")

        f.write("## Change Details (Disk vs. Staging Area)\n\n")
        f.write("| Key | Current (Disk) | Proposed (Staging) |\n")
        f.write("| :--- | :--- | :--- |\n")

        for i, (k, v) in enumerate(accumulated_changes.items()):
            if i >= 100:
                f.write(f"| ... | ... | (+ {len(accumulated_changes) - 100} more keys) |\n")
                break
            old_val = flat_disk.get(k, "*[NEW KEY]*")
            safe_old = str(old_val).replace("\n", "\\n").replace("|", "\\|")
            safe_new = str(v).replace("\n", "\\n").replace("|", "\\|")
            f.write(f"| `{k}` | {safe_old} | **{safe_new}** |\n")

    return SyncProposal(
        proposal_id=lang_code,
        lang_code=lang_code,
        changes_count=len(accumulated_changes),
        diff_summary=accumulated_changes,
        reasoning=combined_reason,
        file_path=file_p,
        validation_errors=val_errs,
        style_suggestions=style_feedbacks,
        preview_file_path=preview_file,
    )


async def save_project_preference(pattern: str, is_native_protection: bool = True):
    """Save user preferences to .i18n-skill.json."""
    config = await _load_project_config()
    if is_native_protection:
        if pattern not in config.protected_lang_key_patterns:
            config.protected_lang_key_patterns.append(pattern)
    else:
        if pattern not in config.ignored_keys:
            config.ignored_keys.append(pattern)

    p = os.path.join(WORKSPACE_ROOT, CONFIG_FILE)
    async with aiofiles.open(p, "w", encoding="utf-8") as f:
        await f.write(json.dumps(config.model_dump(), indent=2, ensure_ascii=False))
    return "Preference saved to config."


async def _load_project_preferences():
    # Compatibility placeholder
    return await _load_project_config()


async def commit_i18n_changes(target_scope: str) -> str:
    """Commit changes and update snapshots. Supports language code or 'all'."""
    proposals_path = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR)
    to_commit = []

    if target_scope.lower() == "all":
        to_commit = glob.glob(os.path.join(proposals_path, "proposal_*.json"))
    else:
        exact_p = os.path.join(proposals_path, f"proposal_{target_scope}.json")
        if os.path.exists(exact_p):
            to_commit = [exact_p]
        else:
            old_p = os.path.join(proposals_path, f"{target_scope}.json")
            if os.path.exists(old_p):
                to_commit = [old_p]
            else:
                pattern = os.path.join(proposals_path, f"proposal_*_{target_scope}.json")
                matches = glob.glob(pattern)
                if matches:
                    to_commit = [matches[0]]
                else:
                    return f"Error: No pending proposals found for scope '{target_scope}'."

    if not to_commit:
        return "No proposals to commit."

    committed_files = []
    snapshot_mgr = TranslationSnapshotManager(WORKSPACE_ROOT)
    for temp_p in to_commit:
        with open(temp_p, encoding="utf-8") as f:
            data = json.load(f)

        safe_target = _validate_safe_path(data["target_file"])
        await _save_locale_data(safe_target, data["content"])

        flattened = _flatten_dict(data["content"])
        content_hash = hashlib.md5(json.dumps(flattened).encode("utf-8")).hexdigest()

        for k, v in flattened.items():
            await snapshot_mgr.update_snapshot(
                key=k,
                translation=v,
                score=10,
                status=TranslationStatus.APPROVED,
                content_hash=content_hash,
            )

        os.remove(temp_p)
        committed_files.append(os.path.basename(safe_target))

    return f"Successfully committed {len(committed_files)} proposals: {', '.join(committed_files)}"


async def optimize_translations(lang_code: str, include_approved: bool = False) -> dict[str, Any]:
    """Export entries for idempotent optimization."""
    config = await _load_project_config()
    target_dir = _detect_locale_dir(config)
    locale_data = await _load_locale_data(target_dir, lang_code)
    flat_data = _flatten_dict(locale_data)

    snapshot_mgr = TranslationSnapshotManager(WORKSPACE_ROOT)
    glossary = {}
    to_optimize = {}

    for k, v in flat_data.items():
        status = await snapshot_mgr.get_status(k)
        if status == TranslationStatus.APPROVED and not include_approved:
            glossary[k] = v
        else:
            to_optimize[k] = v

    os.makedirs(os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR), exist_ok=True)
    task_file = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"optimize_task_{lang_code}.json")

    task_data = {
        "targets": to_optimize,
        "dynamic_glossary": glossary,
        "persona": config.persona.model_dump(),
        "instructions": (
            f"You are translating for a {config.persona.domain} app "
            f"targeting {config.persona.audience} with a {config.persona.tone} tone. "
            "Please read 'targets', provide optimized translations, "
            "and save the result as a new JSON file (key-value pairs only). "
            "Then run 'sync' with the new file path."
        ),
    }

    with open(task_file, "w", encoding="utf-8") as f:
        json.dump(task_data, f, indent=2, ensure_ascii=False)

    return {
        "task_file_path": task_file,
        "message": (
            f"Optimization task exported to {task_file}. "
            f"Found {len(to_optimize)} keys to optimize, "
            f"using {len(glossary)} approved terms as anchor."
        ),
    }


async def generate_quality_report(lang_code: str) -> EvaluationReport:
    """Expert Audit: Generate comprehensive quality report with variable safety check."""
    config = await _load_project_config()
    target_dir = _detect_locale_dir(config)
    locale_data = await _load_locale_data(target_dir, lang_code)
    flat_data = _flatten_dict(locale_data)

    # Load base language for variable consistency check
    base_data = _flatten_dict(await _load_locale_data(target_dir, "en"))

    snapshot_mgr = TranslationSnapshotManager(WORKSPACE_ROOT)
    approved_count = 0
    controversial = []
    error_count = 0

    for k, v in flat_data.items():
        status = await snapshot_mgr.get_status(k)
        if status == TranslationStatus.APPROVED:
            approved_count += 1

        # 1. Variable Mismatch Check (Variable Safety Lock)
        if k in base_data:
            base_placeholders = _extract_placeholders(base_data[k])
            target_placeholders = _extract_placeholders(v)
            if base_placeholders != target_placeholders:
                error_count += 1
                controversial.append(
                    ReviewItem(
                        key=k,
                        current_translation=v,
                        suggested_translation=base_data[k],
                        issue_type="VARIABLE_MISMATCH",
                        confidence="High",
                        reasoning=(
                            f"Base language uses placeholders {list(base_placeholders)}, "
                            f"but target uses {list(target_placeholders)}. "
                            "This will cause rendering errors."
                        ),
                    )
                )

        # 2. Style and Typography Check
        style_feedbacks = TranslationStyleLinter.lint(
            k, v, lang_code, config.protected_lang_key_patterns
        )
        if style_feedbacks:
            for fb in style_feedbacks:
                error_count += 1
                controversial.append(
                    ReviewItem(
                        key=k,
                        current_translation=v,
                        suggested_translation=fb.suggestion,
                        issue_type=f"Style Violation: {fb.violation}",
                        confidence="High",
                        reasoning=fb.message,
                    )
                )

    os.makedirs(os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR), exist_ok=True)
    report_file = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"audit_report_{lang_code}.md")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"# i18n Quality Audit Report ({lang_code})\n\n")
        f.write("## 🎯 Project Persona\n")
        f.write(f"- **Domain**: {config.persona.domain or 'Unset'}\n")
        f.write(f"- **Audience**: {config.persona.audience or 'Unset'}\n")
        f.write(f"- **Tone**: {config.persona.tone or 'Unset'}\n\n")
        f.write("## 📊 Statistics\n")
        f.write(f"- **Total Keys**: {len(flat_data)}\n")
        f.write(f"- **Approved Keys**: {approved_count}\n")
        f.write(f"- **Issues Found**: {error_count}\n\n")
        if error_count > 0:
            f.write("## Detailed Issues\n\n")
            f.write("| Key | Current | Suggestion | Issue Type | Reasoning |\n")
            f.write("| --- | --- | --- | --- | --- |\n")
            for item in controversial:
                safe_curr = item.current_translation.replace("\n", "\\n").replace("|", "\\|")
                safe_sugg = item.suggested_translation.replace("\n", "\\n").replace("|", "\\|")
                f.write(
                    f"| `{item.key}` | `{safe_curr}` | `{safe_sugg}` | "
                    f"{item.issue_type} | {item.reasoning} |\n"
                )
        else:
            f.write("## No issues found!\n\nAll checked items conform to style rules.\n")

    overall_score = max(0, 100 - error_count * 2)

    return EvaluationReport(
        lang_code=lang_code,
        total_keys=len(flat_data),
        approved_keys=approved_count,
        controversial_items=controversial,
        overall_score=overall_score,
        summary=f"Audit complete. Found {error_count} issues. Report saved to {report_file}.",
        report_file_path=report_file,
    )


async def reference_optimize_translations(
    pivot_lang: str, target_lang: str, keys: list[str] | None = None
) -> dict[str, Any]:
    """Cross-language reference optimization."""
    config = await _load_project_config()
    target_dir = _detect_locale_dir(config)

    base_data = _flatten_dict(await _load_locale_data(target_dir, "en"))
    pivot_data = _flatten_dict(await _load_locale_data(target_dir, pivot_lang))
    target_data = _flatten_dict(await _load_locale_data(target_dir, target_lang))

    snapshot_mgr = TranslationSnapshotManager(WORKSPACE_ROOT)
    semantic_mappings = {}

    for k, v in pivot_data.items():
        if k in base_data and (await snapshot_mgr.get_status(k)) == TranslationStatus.APPROVED:
            semantic_mappings[k] = {"base": base_data[k], "reference": v}

    to_optimize = {}
    keys_to_process = keys or target_data.keys()

    for k in keys_to_process:
        if k in target_data and k in semantic_mappings:
            to_optimize[k] = {
                "current": target_data[k],
                "base_context": semantic_mappings[k]["base"],
                "reference_mapping": semantic_mappings[k]["reference"],
            }

    return {
        "targets": to_optimize,
        "reference_lang": pivot_lang,
        "message": (
            f"Anchored to {len(semantic_mappings)} approved semantic mappings from {pivot_lang}."
        ),
    }


async def sync_manual_modifications(lang_code: str) -> str:
    """Feedback Loop: Learn manual edits and promote status to APPROVED."""
    config = await _load_project_config()
    target_dir = _detect_locale_dir(config)
    locale_data = await _load_locale_data(target_dir, lang_code)
    flat_data = _flatten_dict(locale_data)

    snapshot_mgr = TranslationSnapshotManager(WORKSPACE_ROOT)
    snapshots = await snapshot_mgr._read_snapshots()
    updated_count = 0

    for k, v in flat_data.items():
        existing = snapshots.get(k, {})
        old_val = existing.get("translation")
        old_status = existing.get("status")

        if old_val != v or old_status != TranslationStatus.APPROVED.value:
            current_hash = hashlib.md5(v.encode("utf-8")).hexdigest()
            if existing.get("hash") != current_hash:
                await snapshot_mgr.update_snapshot(
                    key=k,
                    translation=v,
                    score=10,
                    status=TranslationStatus.APPROVED,
                    content_hash=current_hash,
                )
                updated_count += 1

    return f"Feedback Loop: Learned {updated_count} manual modifications for '{lang_code}'."


async def get_missing_keys(lang_code: str, base_lang: str = "en") -> dict:
    """Calculate missing entries by comparing with base language."""
    config = await _load_project_config()
    target_dir = _detect_locale_dir(config)

    bd = await _load_locale_data(target_dir, base_lang)
    td = await _load_locale_data(target_dir, lang_code)

    flat_bd = _flatten_dict(bd)
    flat_td = _flatten_dict(td)

    return {k: v for k, v in flat_bd.items() if k not in flat_td}


async def get_dead_keys(lang_code: str = "en") -> list[str]:
    """Identify keys in the locale file that are not used in source code."""
    config = await _load_project_config()
    target_dir = _detect_locale_dir(config)

    # 1. Load all keys from locale file
    locale_data = await _load_locale_data(target_dir, lang_code)
    all_locale_keys = set(_flatten_dict(locale_data).keys())

    if not all_locale_keys:
        return []

    # 2. Scan source code for used keys
    used_keys = set()
    valid_exts = {".js", ".jsx", ".ts", ".tsx", ".vue"}

    source_dirs = config.source_dirs or ["src"]
    for s_dir in source_dirs:
        abs_s_dir = os.path.join(WORKSPACE_ROOT, s_dir)
        if not os.path.exists(abs_s_dir):
            continue

        for root, _, files in os.walk(abs_s_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in valid_exts:
                    fpath = os.path.join(root, file)
                    try:
                        async with aiofiles.open(fpath, encoding="utf-8") as f:
                            content = await f.read()

                        scanner = TreeSitterScanner(content, ext)
                        for text, _, origin in scanner.scan():
                            if origin == "i18n_key":
                                used_keys.add(text)
                    except Exception:
                        continue

    # 3. Calculate difference (Locale Keys - Used Keys)
    dead_keys = sorted(list(all_locale_keys - used_keys))
    return dead_keys


async def _load_locale_data(target_dir: str, lang: str) -> dict:
    """Load locale data across formats (json -> yaml -> ts -> js)"""
    config = await _load_project_config()
    formats = [".json", ".yaml", ".yml", ".ts", ".js"]
    if config.preferred_format:
        pref = config.preferred_format if config.preferred_format.startswith(".") else f".{config.preferred_format}"
        if pref in formats:
            formats.remove(pref)
            formats.insert(0, pref)

    for ext in formats:
        p = _validate_safe_path(os.path.join(target_dir, f"{lang}{ext}"))
        if not os.path.exists(p):
            continue

        try:
            async with aiofiles.open(p, encoding="utf-8") as f:
                content = await f.read()

            if ext == ".json":
                return json.loads(content)

            if ext in (".yaml", ".yml"):
                return yaml.safe_load(content) or {}

            # Use Tree-Sitter for robust TS/JS parsing
            try:
                if not DEPENDENCIES_INSTALLED:
                    raise ImportError("tree-sitter not installed")

                lang_key: str = "tsx" if ext == ".ts" else "javascript"

                # cast to Literal to satisfy tree_sitter_language_pack types
                ts_lang = tree_sitter_language_pack.get_language(cast(Any, lang_key))
                parser = Parser(ts_lang)
                tree = parser.parse(content.encode("utf-8"))

                def get_val(node: Any) -> Any:
                    if node.type == "object":
                        res: dict[str, Any] = {}
                        for child in node.children:
                            if child.type == "pair":
                                key_node = child.child_by_field_name("key")
                                val_node = child.child_by_field_name("value")
                                if not key_node or not val_node:
                                    # Fallback for older tree-sitter or different grammars
                                    key_node = child.children[0]
                                    val_node = child.children[2]

                                k = key_node.text.decode("utf-8").strip("'\"")
                                res[k] = get_val(val_node)
                        return res
                    if node.type == "array":
                        return [get_val(c) for c in node.children if c.type not in ("[", "]", ",")]
                    if node.type == "string":
                        # Strip quotes and handle fragments
                        text = node.text.decode("utf-8")
                        return text[1:-1]
                    if node.type == "number":
                        text = node.text.decode("utf-8")
                        return float(text) if "." in text else int(text)
                    if node.type in ("true", "false", "boolean"):
                        return node.text.decode("utf-8") == "true"
                    if node.type == "null":
                        return None
                    return node.text.decode("utf-8")

                # Find the exported object
                # Common patterns: export default { ... }, module.exports = { ... }
                target_node = None

                # Use query for more robust finding
                query_str = """
                    (export_statement (object) @obj)
                    (expression_statement (assignment_expression left: (member_expression) @mem right: (object) @obj))
                """  # noqa: E501
                query = tree_sitter.Query(ts_lang, query_str)
                cursor = tree_sitter.QueryCursor(query)
                matches = cursor.matches(tree.root_node)

                for _, captures in matches:
                    if "obj" in captures:
                        # Based on investigate_ast, cursor.matches returns a list
                        # where captures values are lists of nodes
                        nodes = captures["obj"]
                        if nodes:
                            target_node = nodes[0]
                            break

                if not target_node:
                    # Alternative: use captures() which returns a list of (node, capture_name)
                    all_captures: list[Any] = cursor.captures(tree.root_node)
                    for c_node, c_name in all_captures:
                        if c_name == "obj":
                            target_node = c_node
                            break

                if not target_node:
                    # Fallback: just find the first object in the tree
                    def find_first_obj(n: Any) -> Any:
                        if n.type == "object":
                            return n
                        for c in n.children:
                            r = find_first_obj(c)
                            if r:
                                return r
                        return None

                    target_node = find_first_obj(tree.root_node)

                if target_node:
                    return get_val(target_node)

            except Exception as e:
                logger.warning(f"AST parser failed for {p}, falling back to regex: {e}")

            # Legacy Regex Fallback (Keep for extreme cases but improved)
            match = re.search(
                r"(?:export\s+default|module\.exports\s*=)\s*({.*});?", content, re.DOTALL
            )
            if match:
                obj_str = match.group(1)
                try:
                    # 1. Clean comments safely
                    obj_str = re.sub(r",\s*([}\]])", r"\1", obj_str)
                    obj_str = obj_str.strip().rstrip(";")
                    return json.loads(obj_str)
                except Exception:
                    return {}
        except Exception as e:
            logger.error(f"Error loading {p}: {e}")
            continue
    return {}


async def _save_locale_data(path: str, data: dict):
    """Write back locale data across formats."""
    ext = os.path.splitext(path)[1].lower()

    if ext in (".ts", ".js"):
        json_str = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
        content = f"export default {json_str};\n"
    elif ext in (".yaml", ".yml"):
        content = yaml.dump(data, allow_unicode=True, sort_keys=True, indent=2)
    else:
        content = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(content)


async def sync_i18n_files(new_pairs: dict, lang_code: str):
    await propose_sync_i18n(new_pairs, lang_code, "Direct sync via CLI")
    return "Synced."


async def refine_i18n_proposal(proposal_id: str, feedback: str) -> str:
    exact_p = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"proposal_{proposal_id}.json")
    if os.path.exists(exact_p):
        temp_p = exact_p
    else:
        old_p = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"{proposal_id}.json")
        if os.path.exists(old_p):
            temp_p = old_p
        else:
            pattern = os.path.join(WORKSPACE_ROOT, PROPOSALS_DIR, f"proposal_*_{proposal_id}.json")
            matches = glob.glob(pattern)
            if matches:
                temp_p = matches[0]
            else:
                return "Error: Proposal not found."

    async with aiofiles.open(temp_p, encoding="utf-8") as f:
        data = json.loads(await f.read())
    data.setdefault("feedback_history", []).append(feedback)
    async with aiofiles.open(temp_p, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False))
    return "Recorded."


# ----------------- Environment Sensing & Support -----------------


async def _load_project_config() -> ProjectConfig:
    p = os.path.join(WORKSPACE_ROOT, CONFIG_FILE)
    if not os.path.exists(p):
        config = ProjectConfig()
        loc_dir = _detect_locale_dir(config)
        detected_langs = _detect_enabled_langs(loc_dir)
        if detected_langs:
            config.enabled_langs = list(set(config.enabled_langs + detected_langs))
        config.locales_dir = loc_dir
        return config

    try:
        async with aiofiles.open(p, encoding="utf-8") as f:
            data = json.loads(await f.read())
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

    # Calculate actual cache size
    cache_count = 0
    cache_path = os.path.join(WORKSPACE_ROOT, CACHE_FILE)
    if os.path.exists(cache_path):
        try:
            async with aiofiles.open(cache_path, encoding="utf-8") as f:
                cache_data = json.loads(await f.read())
                cache_count = len(cache_data)
        except Exception:
            pass

    status_msg = "Ready."
    if not DEPENDENCIES_INSTALLED:
        status_msg = f"Environment Issues: {DEP_ERROR_MSG}"
    elif not has_config_file:
        status_msg = "Ready (Auto-detected). Suggest running 'init' to persist config."

    return ProjectStatus(
        config=config,
        has_glossary=os.path.exists(os.path.join(WORKSPACE_ROOT, GLOSSARY_FILE)),
        cache_size=cache_count,
        workspace_root=WORKSPACE_ROOT,
        status_message=status_msg,
        vcs_info=vcs.get_vcs_status(WORKSPACE_ROOT),
    )


def _detect_locale_dir(config: ProjectConfig) -> str:
    for d in [config.locales_dir, "locales", "src/locales"]:
        if os.path.isdir(os.path.join(WORKSPACE_ROOT, d)):
            return d
    return "locales"


def _detect_enabled_langs(locale_dir: str) -> list[str]:
    """Auto-search for locale files in the locales directory."""
    target = os.path.join(WORKSPACE_ROOT, locale_dir)
    if not os.path.exists(target):
        return []

    langs = []
    pattern = re.compile(r"^([a-zA-Z0-9_-]+)\.(json|ts|js|yaml|yml)$")
    for f in os.listdir(target):
        match = pattern.match(f)
        if match:
            lang_code = match.group(1)
            if lang_code not in ("index", "types"):
                langs.append(lang_code)
    return sorted(list(set(langs)))


async def initialize_project_config(auto: bool = False) -> dict[str, Any]:
    """Scan project and return configuration recommendations."""
    config = ProjectConfig()
    config.locales_dir = _detect_locale_dir(config)
    config.enabled_langs = _detect_enabled_langs(config.locales_dir) or ["en", "zh-CN"]

    for d in ["src", "lib", "app"]:
        if os.path.isdir(os.path.join(WORKSPACE_ROOT, d)):
            config.source_dirs = [d]
            break

    # If auto-mode, finalize persona immediately with safe defaults
    if auto:
        config.persona.domain = "General"
        config.persona.audience = "Global Users"
        config.persona.tone = "Professional"

    ignore_lines = [
        ".i18n-cache.json",
        ".i18n-proposals/",
        ".i18n-snapshots.json",
        ".i18n-prefs.json",
        "!.i18n-skill.json",
    ]

    p = os.path.join(WORKSPACE_ROOT, CONFIG_FILE)
    async with aiofiles.open(p, "w", encoding="utf-8") as f:
        await f.write(json.dumps(config.model_dump(), indent=2, ensure_ascii=False))

    if auto:
        return {
            "message": f"Initialized config with AUTO-PERSONA at {p}.",
            "config": config.model_dump(),
            "status": "ready",
            "next_step": (
                "Configuration is finalized. You can now run 'scan' or 'status' immediately."
            ),
        }

    # AI-Native: Automatically distill project samples to help AI suggest a persona
    project_samples = await distill_project_persona()

    return {
        "message": f"Initialized config at {p}. Processed {len(config.enabled_langs)} languages.",
        "config": config.model_dump(),
        "recommended_gitignore": ignore_lines,
        "project_samples": project_samples,
        "action_required": (
            "Please analyze the 'project_samples', propose a project persona "
            "(domain, audience, tone), and run '/i18n-save-persona' to finalize setup."
        ),
    }


async def load_project_glossary():
    return {}


async def update_project_glossary(t, tr):
    return "Learned"


async def _get_file_hash(p):
    return "hash"


async def distill_project_persona() -> dict[str, Any]:
    """
    [Agentic Distillation] Sample project files to help AI infer the business persona.
    Returns a dict containing README snippets, package.json info, and representative UI keys.
    """
    import random

    config = await _load_project_config()
    samples: dict[str, Any] = {"package_info": {}, "readme_snippet": "", "ui_samples": []}

    # 1. Sample package.json
    pkg_p = os.path.join(WORKSPACE_ROOT, "package.json")
    if os.path.exists(pkg_p):
        try:
            with open(pkg_p, encoding="utf-8") as f:
                pkg = json.load(f)
                samples["package_info"] = {
                    "name": pkg.get("name"),
                    "description": pkg.get("description"),
                    "dependencies": list(pkg.get("dependencies", {}).keys())[:15],
                }
        except Exception:
            pass

    # 2. Sample README.md (Increased context)
    readme_p = os.path.join(WORKSPACE_ROOT, "README.md")
    if os.path.exists(readme_p):
        try:
            async with aiofiles.open(readme_p, encoding="utf-8") as f:
                content = await f.read()
                samples["readme_snippet"] = content[:2000]
        except Exception:
            pass

    # 3. Representative UI Keys from locales
    target_dir = _detect_locale_dir(config)
    en_p = os.path.join(WORKSPACE_ROOT, target_dir, "en.json")
    if os.path.exists(en_p):
        try:
            with open(en_p, encoding="utf-8") as f:
                data = list(_flatten_dict(json.load(f)).items())
                if len(data) <= 20:
                    samples["ui_samples"] = data
                else:
                    # Strategy: First 5 + Random 10 + Top 5 Longest
                    first_5 = data[:5]
                    longest_5 = sorted(data, key=lambda x: len(str(x[1])), reverse=True)[:5]
                    middle_pool = [
                        item for item in data if item not in first_5 and item not in longest_5
                    ]
                    random_10 = random.sample(middle_pool, min(10, len(middle_pool)))
                    samples["ui_samples"] = first_5 + longest_5 + random_10
        except Exception:
            pass

    return samples


async def save_project_persona(persona_data: dict) -> str:
    """Save the confirmed business persona to .i18n-skill.json."""
    config = await _load_project_config()
    config.persona.domain = persona_data.get("domain", config.persona.domain)
    config.persona.audience = persona_data.get("audience", config.persona.audience)
    config.persona.tone = persona_data.get("tone", config.persona.tone)
    config.persona.custom_guidelines = persona_data.get(
        "custom_guidelines", config.persona.custom_guidelines
    )

    p = os.path.join(WORKSPACE_ROOT, CONFIG_FILE)
    async with aiofiles.open(p, "w", encoding="utf-8") as f:
        await f.write(json.dumps(config.model_dump(), indent=2, ensure_ascii=False))

    return "Business persona saved to configuration."


async def _read_cache():
    return {}


async def _write_cache(c):
    pass
