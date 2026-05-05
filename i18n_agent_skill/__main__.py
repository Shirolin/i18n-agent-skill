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
    generate_quality_report,
    get_dead_keys,
    initialize_project_config,
    optimize_translations,
    orchestrate_audit,
    orchestrate_scan,
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
    scan_parser.add_argument(
        "--path",
        help="Path to file or directory to scan (defaults to config source_dirs).",
    )
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
        "--lang",
        default="all",
        help="Target language code (e.g., en, ja) or 'all' for full audit (default: 'all').",
    )
    audit_parser.add_argument("--base", default="en", help="Base language code (defaults to 'en').")

    # 4. sync
    sync_parser = subparsers.add_parser(
        "sync", help="Generate a translation synchronization proposal."
    )
    sync_parser.add_argument("--lang", required=True, help="Target language.")
    sync_parser.add_argument(
        "--data", required=True, help="JSON string of key-value pairs or a file path."
    )
    sync_parser.add_argument("--reason", default="Manual sync", help="Reason for changes.")

    # 5. commit
    commit_parser = subparsers.add_parser("commit", help="Commit and apply specified proposals.")
    commit_parser.add_argument(
        "--proposal", required=True, help="Proposal ID (language code or 'all')."
    )

    # 6. init
    init_parser = subparsers.add_parser(
        "init", help="Scan project and generate explicit .i18n-skill.json configuration."
    )
    init_parser.add_argument(
        "--auto",
        action="store_true",
        help="One-step setup: automatically infer persona and finalize configuration.",
    )

    # 7. optimize
    opt_parser = subparsers.add_parser(
        "optimize", help="[Idempotent] Export targets for optimization."
    )
    opt_parser.add_argument("--lang", required=True, help="Target language code.")
    opt_parser.add_argument(
        "--all", action="store_true", help="Include approved keys for full polish."
    )

    # 8. learn
    learn_parser = subparsers.add_parser(
        "learn", help="[Feedback Loop] Detect manual edits and promote entry status."
    )
    learn_parser.add_argument("--lang", required=True, help="Target language code.")

    # 9. audit-quality
    audit_q_parser = subparsers.add_parser(
        "audit-quality", help="[Expert Audit] Generate a full quality review report."
    )
    audit_q_parser.add_argument("--lang", required=True, help="Target language code.")

    # 10. pivot-sync
    pivot_parser = subparsers.add_parser(
        "pivot-sync",
        help="[Reference Sync] Optimize target language based on familiar language mappings.",
    )
    pivot_parser.add_argument("--pivot", required=True, help="Reference language (e.g., zh-CN).")
    pivot_parser.add_argument("--target", required=True, help="Target language (e.g., ja).")

    # 11. distill-persona
    subparsers.add_parser(
        "distill-persona", help="[Agentic] Sample project to help AI infer business persona."
    )

    # 12. save-persona
    save_p_parser = subparsers.add_parser("save-persona", help="Save confirmed business persona.")
    save_p_parser.add_argument(
        "--data", required=True, help="JSON string of persona (domain, audience, tone)."
    )

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
        init_res = await initialize_project_config(auto=args.auto)
        _print_json(init_res)

    elif args.command == "optimize":
        status_report = await check_project_status()
        if args.lang not in status_report.config.enabled_langs:
            _print_json(
                {
                    "error": (
                        f"Language '{args.lang}' is not enabled in this project. "
                        "Use 'init' or update .i18n-skill.json."
                    )
                }
            )
            return

        opt_res = await optimize_translations(args.lang, include_approved=args.all)
        _print_json(opt_res)

    elif args.command == "learn":
        status_report = await check_project_status()
        if args.lang not in status_report.config.enabled_langs:
            _print_json({"error": f"Language '{args.lang}' is not enabled in this project."})
            return
        learn_msg = await sync_manual_modifications(args.lang)
        _print_json({"message": learn_msg})

    elif args.command == "audit-quality":
        status_report = await check_project_status()
        if args.lang not in status_report.config.enabled_langs:
            _print_json({"error": f"Language '{args.lang}' is not enabled in this project."})
            return
        quality_res = await generate_quality_report(args.lang)
        _print_json(quality_res.model_dump())

    elif args.command == "pivot-sync":
        status_report = await check_project_status()
        if args.pivot not in status_report.config.enabled_langs:
            _print_json({"error": f"Pivot language '{args.pivot}' is not enabled."})
            return
        if args.target not in status_report.config.enabled_langs:
            _print_json({"error": f"Target language '{args.target}' is not enabled."})
            return
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
        scan_res = await orchestrate_scan(
            path=args.path, use_cache=args.use_cache, vcs_mode=args.vcs
        )
        _print_json(scan_res)

    elif args.command == "audit":
        audit_res = await orchestrate_audit(lang_code=args.lang, base_lang=args.base)
        _print_json(audit_res)

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
        commit_msg = await commit_i18n_changes(args.proposal)
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
