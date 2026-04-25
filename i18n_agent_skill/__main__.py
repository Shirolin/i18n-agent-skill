import argparse
import asyncio
import json
import os
import subprocess
import sys
from typing import Any


# =================================================================
# [Venv Bootstrapper] 确保在隔离环境中运行，防止系统 Python 逃逸
# =================================================================
def bootstrap_venv():
    # 查找技能根目录（即包含 .venv 的目录）
    skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    venv_path = os.path.join(skill_root, ".venv")

    if os.path.exists(venv_path):
        # 确定 venv 中的 python 路径
        if sys.platform == "win32":
            venv_python = os.path.join(venv_path, "Scripts", "python.exe")
        else:
            venv_python = os.path.join(venv_path, "bin", "python")

        if os.path.exists(venv_python):
            # 获取当前运行的 python 路径
            current_python = os.path.abspath(sys.executable)
            target_python = os.path.abspath(venv_python)

            # 如果当前 python 不是 venv 中的 python，且不是通过 venv python 递归调用的
            if current_python != target_python and os.environ.get("I18N_SKILL_BOOTSTRAPPED") != "1":
                # 设置环境变量防止死循环
                env = os.environ.copy()
                env["I18N_SKILL_BOOTSTRAPPED"] = "1"
                # 重新通过 venv python 启动自己
                # 注：使用 sys.argv 完美透传所有参数
                cmd = [target_python, "-m", "i18n_agent_skill"] + sys.argv[1:]
                sys.exit(subprocess.call(cmd, env=env))


bootstrap_venv()
# =================================================================


from i18n_agent_skill import tools  # noqa: E402
from i18n_agent_skill.tools import (  # noqa: E402
    check_project_status,
    commit_i18n_changes,
    extract_raw_strings,
    generate_quality_report,
    get_missing_keys,
    initialize_project_config,
    optimize_translations,
    propose_sync_i18n,
    reference_optimize_translations,
    sync_manual_modifications,
)


def _print_json(data: Any):
    """确保输出是 AI 可解析的 JSON"""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


async def cli_main():
    parser = argparse.ArgumentParser(description="I18n Agent Skill 引擎 v0.1.0")
    parser.add_argument(
        "--workspace-root", type=str, help="显式指定项目根目录，在嵌套结构下推荐使用"
    )
    subparsers = parser.add_subparsers(dest="command", help="支持的子命令")

    # 1. status
    subparsers.add_parser("status", help="检查当前项目 i18n 状态及环境感知")

    # 2. scan
    scan_parser = subparsers.add_parser("scan", help="扫描源码中的硬编码中文并执行隐私脱敏")
    scan_parser.add_argument("path", help="待扫描的文件或目录路径")
    scan_parser.add_argument(
        "--vcs", action="store_true", help="开启 VCS 感知模式，仅扫描 Git 变动"
    )
    scan_parser.add_argument(
        "--no-cache", action="store_false", dest="use_cache", help="禁用哈希缓存"
    )

    # 3. audit
    audit_parser = subparsers.add_parser("audit", help="比对语言包差异，查找缺失的 Key")
    audit_parser.add_argument("lang", help="目标对比语言代码 (如 en, ja) 或使用 'all' 执行全量体检")
    audit_parser.add_argument("--base", default="en", help="基准语言代码 (默认 en)")

    # 4. sync
    sync_parser = subparsers.add_parser("sync", help="生成翻译同步提案")
    sync_parser.add_argument("lang", help="目标语言")
    sync_parser.add_argument("data", help="JSON 格式的键值对字符串或路径")
    sync_parser.add_argument("--reason", default="Manual sync", help="变更理由")

    # 5. commit
    commit_parser = subparsers.add_parser("commit", help="正式提交并应用指定的提案")
    commit_parser.add_argument("proposal_id", help="提案 ID")

    # 6. init
    subparsers.add_parser("init", help="扫描项目并生成显式的 .i18n-skill.json 配置文件")

    # 7. optimize
    opt_parser = subparsers.add_parser("optimize", help="[幂等优化] 筛选待优化词条并提取动态术语")
    opt_parser.add_argument("lang", help="目标语言代码")
    opt_parser.add_argument("--all", action="store_true", help="强制包含已确认的词条进行全量优化")

    # 8. learn
    learn_parser = subparsers.add_parser("learn", help="[闭环反馈] 探测手动修改并提升词条状态")
    learn_parser.add_argument("lang", help="目标语言代码")

    audit_q_parser = subparsers.add_parser("audit-quality", help="[专家巡检] 生成全量质量评审报告")
    audit_q_parser.add_argument("lang", help="目标语言代码")

    # 10. pivot-sync
    pivot_parser = subparsers.add_parser(
        "pivot-sync", help="[参照优化] 根据已知语言映射优化目标语言"
    )
    pivot_parser.add_argument("pivot", help="参考语言 (如 zh-CN)")
    pivot_parser.add_argument("target", help="目标语言 (如 ja)")

    # 11. mcp
    subparsers.add_parser("mcp", help="以 MCP Server 模式运行")

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
            # [核心修复] 实现 audit all 逻辑
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
            _print_json(missing_keys)

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
