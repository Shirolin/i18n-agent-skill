import argparse
import asyncio
import json
import os
import sys
from typing import Any

from i18n_agent_skill.tools import (
    check_project_status,
    extract_raw_strings,
    get_missing_keys,
    propose_sync_i18n,
    commit_i18n_changes
)

def _print_json(data: Any):
    """确保输出是 AI 可解析的 JSON"""
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))

async def cli_main():
    parser = argparse.ArgumentParser(description="i18n-agent-skill CLI: 自动化国际化工程工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 1. status
    subparsers.add_parser("status", help="检查当前项目 i18n 状态及环境感知")

    # 2. scan
    scan_parser = subparsers.add_parser("scan", help="扫描源码中的硬编码中文并执行隐私脱敏")
    scan_parser.add_argument("path", help="待扫描的文件或目录路径")
    scan_parser.add_argument("--vcs", action="store_true", help="开启 VCS 感知模式，仅扫描 Git 变动")
    scan_parser.add_argument("--no-cache", action="store_false", dest="use_cache", help="禁用哈希缓存")

    # 3. audit
    audit_parser = subparsers.add_parser("audit", help="比对语言包差异，查找缺失的 Key")
    audit_parser.add_argument("lang", help="目标对比语言代码 (如 en, ja)")
    audit_parser.add_argument("--base", default="en", help="基准语言代码 (默认 en)")

    # 4. sync
    sync_parser = subparsers.add_parser("sync", help="生成翻译同步提案")
    sync_parser.add_argument("lang", help="目标语言")
    sync_parser.add_argument("data", help="JSON 格式的键值对字符串或路径")
    sync_parser.add_argument("--reason", default="Manual sync", help="变更理由")

    # 5. commit
    commit_parser = subparsers.add_parser("commit", help="正式提交并应用指定的提案")
    commit_parser.add_argument("proposal_id", help="提案 ID")

    # 6. mcp (旧模式，保持兼容)
    subparsers.add_parser("mcp", help="以 MCP Server 模式运行（兼容 Cursor/Cline）")

    # 7. update
    subparsers.add_parser("update", help="[Internal] AI 内部调用的更新入口")

    args = parser.parse_args()

    if args.command == "status":
        res = await check_project_status()
        _print_json(res.model_dump())
    
    elif args.command == "scan":
        res = await extract_raw_strings(args.path, use_cache=args.use_cache, vcs_mode=args.vcs)
        _print_json(res.model_dump())

    elif args.command == "audit":
        res = await get_missing_keys(args.lang, base_lang=args.base)
        _print_json(res)

    elif args.command == "sync":
        try:
            new_pairs = json.loads(args.data)
        except json.JSONDecodeError:
            # 尝试作为文件读取
            with open(args.data, 'r', encoding='utf-8') as f:
                new_pairs = json.load(f)
        res = await propose_sync_i18n(new_pairs, args.lang, args.reason)
        _print_json(res.model_dump())

    elif args.command == "commit":
        res = await commit_i18n_changes(args.proposal_id)
        print(res)

    elif args.command == "mcp":
        from i18n_agent_skill.mcp_server import mcp
        mcp.run()

    elif not args.command:
        # 如果没有任何参数，默认运行 MCP 以保持向后兼容性
        from i18n_agent_skill.mcp_server import mcp
        mcp.run()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(cli_main())
