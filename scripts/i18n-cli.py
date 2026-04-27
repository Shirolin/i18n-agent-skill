#!/usr/bin/env python3
"""
i18n-cli.py — Standard CLI entry point for i18n-agent-skill.
Wraps the core module and adds system readiness checks.
"""

import importlib.util
import sys


def check_readiness():
    """Check if the environment is ready."""
    if importlib.util.find_spec("i18n_agent_skill") is None:
        print("[ERROR] i18n_agent_skill module is not installed.")
        print("Please run: pip install -e .")
        return False
    return True


def run_main():
    """Invoke the core entry point."""
    if not check_readiness():
        sys.exit(1)

    import asyncio

    from i18n_agent_skill.__main__ import cli_main

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(cli_main())


if __name__ == "__main__":
    run_main()
