import argparse
import asyncio
import json
import os
import subprocess
import sys
from typing import Any


# =================================================================
# [Venv Bootstrapper] Ensures running in isolated environment
# =================================================================
def bootstrap_venv():
    # Find skill root (directory containing .venv)
    skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    venv_path = os.path.join(skill_root, ".venv")

    if os.path.exists(venv_path):
        # Determine python path in venv
        if sys.platform == "win32":
            venv_python = os.path.join(venv_path, "Scripts", "python.exe")
        else:
            venv_python = os.path.join(venv_path, "bin", "python")

        if os.path.exists(venv_python):
            # Get current python path
            current_python = os.path.abspath(sys.executable)
            target_python = os.path.abspath(venv_python)

            # Re-launch with venv python if not already running it
            if current_python != target_python and os.environ.get("I18N_SKILL_BOOTSTRAPPED") != "1":
                env = os.environ.copy()
                env["I18N_SKILL_BOOTSTRAPPED"] = "1"
                cmd = [target_python, "-m", "i18n_agent_skill"] + sys.argv[1:]
                sys.exit(subprocess.call(cmd, env=env))


bootstrap_venv()
# =================================================================


from i18n_agent_skill import tools  # noqa: E402
from i18n_agent_skill.tools import (  # noqa: E402
    check_project_status,
    commit_i18n_changes,
    distill_project_persona,
    extract_raw_strings,
    generate_quality_report,
    get_dead_keys,
    get_missing_keys,
    initialize_project_config,
    optimize_translations,
    propose_sync_i18n,
    reference_optimize_translations,
    save_project_persona,
    sync_manual_modifications,
)


def _print_json(data: Any):
    """Ensure output is AI-parseable JSON, forced to UTF-8 encoding."""
    json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    try:
        print(json_str)
    except UnicodeEncodeError:
        # Fallback: Write directly to byte stream if stdout is not UTF-8
        sys.stdout.buffer.write(json_str.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()


async def cli_main():
    # [Windows Special] Force UTF-8 for stdout/stderr to avoid encoding crashes
    if sys.platform == "win32":
        import io

        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        if hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    parser = argparse.ArgumentParser(description="I18n Agent Skill Engine v0.1.0")
    parser.add_argument(
        "--workspace-root",
        type=str,
        help="Explicitly specify project root (recommended for nested projects).",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 1. status
    subparsers.add_parser("status", help="Check current project i18n status and environment.")

    # 2. scan
    scan_parser = subparsers.add_parser(
        "scan", help="Scan source code for hardcoded strings and mask sensitive data."
    )
    scan_parser.add_argument("path", help="Path to file or directory to scan.")
    scan_parser.add_argument(
        "--vcs", action="store_true", help="Enable VCS-aware mode (scan Git changes only)."
    )
    scan_parser.add_argument(
        "--no-cache", action="store_false", dest="use_cache", help="Disable hash caching."
    )

    # 3. audit
    audit_parser = subparsers.add_parser(
        "audit", help="Compare locale files and find missing keys."
    )
    audit_parser.add_argument(
        "lang", help="Target language code (e.g., en, ja) or 'all' for full audit."
    )
    audit_parser.add_argument("--base", default="en", help="Base language code (defaults to 'en').")

    # 4. sync
    sync_parser = subparsers.add_parser(
        "sync", help="Generate a translation synchronization proposal."
    )
    sync_parser.add_argument("lang", help="Target language.")
    sync_parser.add_argument("data", help="JSON string of key-value pairs or a file path.")
    sync_parser.add_argument("--reason", default="Manual sync", help="Reason for changes.")

    # 5. commit
    commit_parser = subparsers.add_parser("commit", help="Commit and apply specified proposals.")
    commit_parser.add_argument("proposal_id", help="Proposal ID (language code or 'all').")

    # 6. init
    subparsers.add_parser(
        "init", help="Scan project and generate explicit .i18n-skill.json configuration."
    )

    # 7. optimize
    opt_parser = subparsers.add_parser(
        "optimize", help="[Idempotent] Export targets for optimization."
    )
    opt_parser.add_argument("lang", help="Target language code.")
    opt_parser.add_argument(
        "--all", action="store_true", help="Include approved keys for full polish."
    )

    # 8. learn
    learn_parser = subparsers.add_parser(
        "learn", help="[Feedback Loop] Detect manual edits and promote entry status."
    )
    learn_parser.add_argument("lang", help="Target language code.")

    # 9. audit-quality
    audit_q_parser = subparsers.add_parser(
        "audit-quality", help="[Expert Audit] Generate a full quality review report."
    )
    audit_q_parser.add_argument("lang", help="Target language code.")

    # 10. pivot-sync
    pivot_parser = subparsers.add_parser(
        "pivot-sync",
        help="[Reference Sync] Optimize target language based on familiar language mappings.",
    )
    pivot_parser.add_argument("pivot", help="Reference language (e.g., zh-CN).")
    pivot_parser.add_argument("target", help="Target language (e.g., ja).")

    # 11. distill-persona
    subparsers.add_parser(
        "distill-persona", help="[Agentic] Sample project to help AI infer business persona."
    )

    # 12. save-persona
    save_p_parser = subparsers.add_parser("save-persona", help="Save confirmed business persona.")
    save_p_parser.add_argument("data", help="JSON string of persona (domain, audience, tone).")

    # 13. cleanup
    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Identify and report dead (unused) i18n keys."
    )
    cleanup_parser.add_argument(
        "--lang", default="en", help="Language to check for dead keys (defaults to 'en')."
    )

    # 14. mcp
    subparsers.add_parser("mcp", help="Run as MCP Server.")

    args = parser.parse_args()

    if args.workspace_root:
        tools.set_workspace_root(args.workspace_root)

    if args.command == "status":
        status_res = await check_project_status()
        _print_json(status_res.model_dump())

    elif args.command == "init":
        init_msg = await initialize_project_config()
        _print_json({"message": init_msg})

    elif args.command == "optimize":
        opt_res = await optimize_translations(args.lang, include_approved=args.all)
        _print_json(opt_res)

    elif args.command == "learn":
        learn_msg = await sync_manual_modifications(args.lang)
        _print_json({"message": learn_msg})

    elif args.command == "audit-quality":
        quality_res = await generate_quality_report(args.lang)
        _print_json(quality_res.model_dump())

    elif args.command == "pivot-sync":
        pivot_res = await reference_optimize_translations(args.pivot, args.target)
        _print_json(pivot_res)

    elif args.command == "distill-persona":
        samples = await distill_project_persona()
        _print_json(samples)

    elif args.command == "save-persona":
        try:
            p_data = json.loads(args.data)
            save_res = await save_project_persona(p_data)
            _print_json({"message": save_res})
        except json.JSONDecodeError:
            _print_json({"error": "Invalid JSON string for persona data."})

    elif args.command == "cleanup":
        dead_keys = await get_dead_keys(lang_code=args.lang)
        _print_json(
            {
                "language": args.lang,
                "dead_keys_count": len(dead_keys),
                "dead_keys": dead_keys,
                "message": (
                    f"Found {len(dead_keys)} unused keys in '{args.lang}'. "
                    "Suggest pruning these to reduce technical debt."
                ),
            }
        )

    elif args.command == "scan":
        if os.path.isdir(args.path):
            all_results = []
            total_tel: dict[str, float | int] = {
                "duration_ms": 0.0,
                "files_processed": 0,
                "keys_extracted": 0,
                "privacy_shield_hits": 0,
            }
            valid_exts = {".js", ".jsx", ".ts", ".tsx", ".vue"}
            for root, _, files in os.walk(args.path):
                for file in files:
                    if os.path.splitext(file)[1].lower() in valid_exts:
                        fpath = os.path.join(root, file)
                        scan_res = await extract_raw_strings(
                            fpath, use_cache=args.use_cache, vcs_mode=args.vcs
                        )
                        if scan_res.results:
                            all_results.extend([r.model_dump() for r in scan_res.results])
                        if scan_res.telemetry:
                            total_tel["duration_ms"] += scan_res.telemetry.duration_ms
                            total_tel["files_processed"] += scan_res.telemetry.files_processed
                            total_tel["keys_extracted"] += scan_res.telemetry.keys_extracted
                            if getattr(scan_res.telemetry, "privacy_shield_hits", None):
                                total_tel["privacy_shield_hits"] += int(
                                    scan_res.telemetry.privacy_shield_hits
                                )
            _print_json({"results": all_results, "telemetry": total_tel})
        else:
            single_res = await extract_raw_strings(
                args.path, use_cache=args.use_cache, vcs_mode=args.vcs
            )
            _print_json(single_res.model_dump())

    elif args.command == "audit":
        if args.lang == "all":
            status_report = await check_project_status()
            target_langs = status_report.config.enabled_langs
            audit_results = {}
            for target_l in target_langs:
                if target_l == args.base:
                    continue
                missing_keys = await get_missing_keys(target_l, base_lang=args.base)
                audit_results[target_l] = {
                    "missing_count": len(missing_keys),
                    "missing_keys": missing_keys,
                }
            _print_json(audit_results)
        else:
            missing_keys = await get_missing_keys(args.lang, base_lang=args.base)
            dead_keys = await get_dead_keys(lang_code=args.lang)
            _print_json(
                {
                    "language": args.lang,
                    "missing_keys_count": len(missing_keys),
                    "missing_keys": missing_keys,
                    "dead_keys_count": len(dead_keys),
                    "message": (
                        f"Audit complete for '{args.lang}'. "
                        f"Found {len(missing_keys)} missing and "
                        f"{len(dead_keys)} unused keys."
                    ),
                }
            )

    elif args.command == "sync":
        try:
            new_pairs = json.loads(args.data)
        except json.JSONDecodeError:
            if os.path.isfile(args.data):
                with open(args.data, encoding="utf-8") as f:
                    new_pairs = json.load(f)
            else:
                _print_json(
                    {
                        "error": "Invalid JSON string or file not found. "
                        "If using literal JSON in PowerShell, watch out for quote stripping."
                    }
                )
                return
        sync_res = await propose_sync_i18n(new_pairs, args.lang, args.reason)
        _print_json(sync_res.model_dump())

    elif args.command == "commit":
        commit_msg = await commit_i18n_changes(args.proposal_id)
        print(commit_msg)

    elif args.command == "mcp":
        from i18n_agent_skill.mcp_server import mcp

        mcp.run()

    elif not args.command:
        from i18n_agent_skill.mcp_server import mcp

        mcp.run()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(cli_main())
