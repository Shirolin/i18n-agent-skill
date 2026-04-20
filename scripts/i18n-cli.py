#!/usr/bin/env python3
"""
i18n-cli.py — i18n-agent-skill 标准命令行入口
封装了核心模块并增加了系统就绪检查。
"""

import importlib.util
import sys


def check_readiness():
    """检查环境是否就绪"""
    if importlib.util.find_spec("i18n_agent_skill") is None:
        print("[ERROR] i18n_agent_skill 模块未安装。")
        print("请运行: pip install -e .")
        return False
    return True


def run_main():
    """调用核心入口"""
    if not check_readiness():
        sys.exit(1)

    import asyncio

    from i18n_agent_skill.__main__ import cli_main

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(cli_main())


if __name__ == "__main__":
    run_main()
