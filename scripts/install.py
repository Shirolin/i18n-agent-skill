#!/usr/bin/env python3
"""
install.py — i18n-agent-skill cross-platform installer.
Replaces install-skill.sh and bootstrap.ps1.

Usage:
  ./install.sh                    # Default: setup Python env (after git clone)
  ./install.sh --dev              # Dev mode: symlink to ~/.agents/skills/
  ./install.sh --dev --workspace  # Dev mode: also symlink to CWD/.agents/skills/
  ./install.sh --link-platforms   # Create platform symlinks from ADK path
  ./install.sh --update           # git pull + re-setup
  ./install.sh --check            # Check for available updates
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_NAME = "i18n-agent-skill"
REPO_URL = "https://github.com/Shirolin/i18n-agent-skill"

# ANSI colors — disabled on Windows cmd
_use_color = sys.platform != "win32" or bool(os.environ.get("TERM"))
BLUE = "\033[0;34m" if _use_color else ""
GREEN = "\033[0;32m" if _use_color else ""
YELLOW = "\033[0;33m" if _use_color else ""
RED = "\033[0;31m" if _use_color else ""
BOLD = "\033[1m" if _use_color else ""
NC = "\033[0m" if _use_color else ""


def info(msg: str) -> None:
    print(f"{BLUE}[INFO]{NC}  {msg}")


def ok(msg: str) -> None:
    print(f"{GREEN}[OK]{NC}    {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{NC}  {msg}")


def error(msg: str) -> None:
    print(f"{RED}[ERROR]{NC} {msg}")


# Root of the skill repo: parent of the scripts/ directory
SKILL_ROOT = Path(__file__).parent.parent.resolve()


# ---------------------------------------------------------------------------
# Python environment
# ---------------------------------------------------------------------------


def find_python() -> str:
    """Return the first Python 3.8+ executable found on PATH."""
    for candidate in ("python3", "python"):
        try:
            result = subprocess.run(
                [candidate, "-c", "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"],
                capture_output=True,
            )
            if result.returncode == 0:
                return candidate
        except FileNotFoundError:
            continue
    error("Python 3.8+ is required but not found.")
    error("Install Python from https://python.org and re-run.")
    sys.exit(1)


def pre_flight_check() -> None:
    """Verify that essential Python modules like 'venv' are available."""
    info("Performing pre-flight environment check…")
    python = find_python()
    try:
        # Check for venv module
        subprocess.run(
            [python, "-c", "import venv"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        error("Python 'venv' module is missing or broken.")
        if sys.platform == "win32":
            error(
                "Please re-install Python from https://python.org and "
                "ensure 'pip' and 'venv' are checked."
            )
        else:
            error(
                "Please install the venv package (e.g., 'sudo apt install python3-venv' on Ubuntu)."
            )
        sys.exit(1)
    ok("Environment pre-check passed.")


def setup_venv() -> None:
    """Create .venv and install package in editable mode."""
    pre_flight_check()
    info("Setting up Python environment…")
    venv_dir = SKILL_ROOT / ".venv"
    python = find_python()

    if not venv_dir.exists():
        subprocess.run([python, "-m", "venv", str(venv_dir)], check=True)

    if sys.platform == "win32":
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:
        venv_python = venv_dir / "bin" / "python"

    if not venv_python.exists():
        error("Failed to create virtual environment.")
        sys.exit(1)

    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "--quiet"],
        check=True,
    )
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-e", str(SKILL_ROOT), "--quiet"],
        check=True,
    )
    ok("Python environment ready.")


# ---------------------------------------------------------------------------
# Project root detection & .gitignore patching
# ---------------------------------------------------------------------------


def detect_project_root() -> Path | None:
    """
    If this skill is installed inside a project's .agents/skills/, return the
    project root. Expected structure: <project>/.agents/skills/i18n-agent-skill/
    """
    # SKILL_ROOT.parent = .agents/skills/
    # SKILL_ROOT.parent.parent = .agents/
    skills_dir = SKILL_ROOT.parent
    agents_dir = skills_dir.parent
    if skills_dir.name == "skills" and agents_dir.name == ".agents":
        return agents_dir.parent
    return None


def patch_gitignore() -> None:
    """Append `.agents/` and runtime files to the project's .gitignore if not already present."""
    project_root = detect_project_root()
    if project_root is None:
        return  # Global install or dev mode — nothing to patch

    gitignore = project_root / ".gitignore"
    # Define rules to ensure clean project state
    rules = [
        "# Agent skills (not tracked with this project)",
        ".agents/",
        "# i18n-agent-skill runtime files",
        ".i18n-cache.json",
        ".i18n-proposals/",
        ".i18n-snapshots.json",
        ".i18n-prefs.json",
        "!.i18n-skill.json",
    ]

    existing_content = ""
    if gitignore.exists():
        existing_content = gitignore.read_text(encoding="utf-8")

    to_add = []
    for rule in rules:
        if rule not in existing_content:
            to_add.append(rule)

    if to_add:
        with gitignore.open("a", encoding="utf-8") as f:
            if existing_content and not existing_content.endswith("\n"):
                f.write("\n")
            f.write("\n" + "\n".join(to_add) + "\n")
        ok(f"Patched {gitignore}")


def generate_command_proxy() -> None:
    """Generate root-level i18n proxy scripts for easier CLI access."""
    project_root = detect_project_root()
    if project_root is None:
        return

    # Path to the venv python relative to project root
    try:
        rel_skill_path = SKILL_ROOT.relative_to(project_root)
    except ValueError:
        return  # Not installed in expected project structure

    if sys.platform == "win32":
        proxy_path = project_root / "i18n.ps1"
        venv_python = rel_skill_path / ".venv" / "Scripts" / "python.exe"
        content = f'& "$PSScriptRoot\\{venv_python}" -m i18n_agent_skill $args\n'
    else:
        proxy_path = project_root / "i18n"
        venv_python = rel_skill_path / ".venv" / "bin" / "python"
        content = f'#!/bin/sh\nexec "$(dirname "$0")/{venv_python}" -m i18n_agent_skill "$@"\n'

    proxy_path.write_text(content, encoding="utf-8")
    if sys.platform != "win32":
        os.chmod(proxy_path, 0o755)

    ok(f"Generated command proxy: {proxy_path.name}")


# ---------------------------------------------------------------------------
# Git checks
# ---------------------------------------------------------------------------


def check_git_repo() -> None:
    """Warn if not a git repository — updates will not work."""
    result = subprocess.run(
        ["git", "-C", str(SKILL_ROOT), "rev-parse", "--git-dir"],
        capture_output=True,
    )
    if result.returncode != 0:
        warn("This directory is not a git repository.")
        warn("Automatic update notifications will not work.")
        warn("For a git-based install, use:")
        warn(f"  git clone --depth 1 {REPO_URL} <install_path>")


def check_for_update() -> None:
    """Silently compare local HEAD vs remote HEAD and notify if different."""
    try:
        r_local = subprocess.run(
            ["git", "-C", str(SKILL_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        r_remote = subprocess.run(
            ["git", "-C", str(SKILL_ROOT), "ls-remote", "origin", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r_local.returncode != 0 or r_remote.returncode != 0:
            return
        local_hash = r_local.stdout.strip()
        remote_line = r_remote.stdout.strip()
        remote_hash = remote_line.split()[0] if remote_line else ""
        if remote_hash and local_hash != remote_hash:
            print(
                f"\n{YELLOW}i{NC} i18n-agent-skill 有新版本可用。运行以下命令更新：\n"
                f"  cd {SKILL_ROOT} && git pull && ./install.sh\n"
            )
    except Exception:
        pass  # Network unavailable or no git — skip silently


def do_update() -> None:
    """Pull latest commits and re-initialize the Python environment."""
    info("Pulling latest updates…")
    result = subprocess.run(["git", "-C", str(SKILL_ROOT), "pull"], check=False)
    if result.returncode == 0:
        ok("Repository updated.")
        setup_venv()
    else:
        error("git pull failed. Check your network connection and try again.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Symlink helpers
# ---------------------------------------------------------------------------


def create_symlink(src: Path, dst: Path) -> None:
    """Create a symlink (or NTFS junction on Windows) from dst -> src."""
    if dst.exists() or dst.is_symlink():
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        else:
            shutil.rmtree(dst)

    dst.parent.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        # mklink /J works without administrator privileges
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(dst), str(src)],
            capture_output=True,
        )
        if result.returncode != 0:
            # Fallback to copy
            shutil.copytree(str(src), str(dst))
            warn(f"Junction failed, copied instead: {dst}")
            return
    else:
        dst.symlink_to(src)

    ok(f"Linked: {dst}")


# ---------------------------------------------------------------------------
# Deployment modes
# ---------------------------------------------------------------------------


def do_dev(workspace: bool = False) -> None:
    """
    Developer mode: symlink SKILL_ROOT into ADK standard paths so that edits
    to the source are immediately reflected without reinstalling.

    --dev            -> ~/.agents/skills/<skill>
    --dev --workspace -> additionally CWD/.agents/skills/<skill>
    """
    targets = [Path.home() / ".agents" / "skills" / SKILL_NAME]

    if workspace:
        cwd_target = Path.cwd() / ".agents" / "skills" / SKILL_NAME
        targets.append(cwd_target)

    for target in targets:
        if target.resolve() == SKILL_ROOT:
            warn(f"Skipping self-referential symlink: {target}")
            continue
        create_symlink(SKILL_ROOT, target)


# Platform-specific skills directories (besides the ADK standard path)
_PLATFORM_SKILLS_DIRS = {
    "gemini": Path.home() / ".gemini" / "skills",
    "claude": Path.home() / ".claude" / "skills",
}


def do_link_platforms() -> None:
    """
    Create symlinks from platform-specific paths to the ADK universal path.
    Only operates on platform dirs that already exist on this system.
    """
    global_adk = Path.home() / ".agents" / "skills" / SKILL_NAME
    if not global_adk.exists() and not global_adk.is_symlink():
        warn(f"ADK global path not found: {global_adk}")
        warn("Run './install.sh --dev' first to install to the ADK path.")
        return

    linked = 0
    for platform, skills_dir in _PLATFORM_SKILLS_DIRS.items():
        if not skills_dir.exists():
            continue
        target = skills_dir / SKILL_NAME
        try:
            if target.resolve() == global_adk.resolve():
                info(f"Already linked ({platform}): {target}")
                continue
        except OSError:
            pass
        create_symlink(global_adk, target)
        linked += 1

    if linked == 0:
        info("No additional platform directories detected (gemini, claude).")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="install.py",
        description=f"{SKILL_NAME} — cross-platform installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  ./install.sh                 # Setup Python env after git clone\n"
            "  ./install.sh --dev           # Dev: symlink to ~/.agents/skills/\n"
            "  ./install.sh --dev --workspace  # Dev: also link to CWD/.agents/skills/\n"
            "  ./install.sh --link-platforms   # Optional platform symlinks\n"
            "  ./install.sh --update        # Pull updates + re-setup\n"
            "  ./install.sh --check         # Check for available updates\n"
        ),
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Developer mode: symlink source to ~/.agents/skills/",
    )
    parser.add_argument(
        "--workspace",
        action="store_true",
        help="(with --dev) Also symlink to CWD/.agents/skills/",
    )
    parser.add_argument(
        "--link-platforms",
        action="store_true",
        help="Create symlinks from platform-specific dirs to ADK path",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Pull latest updates from remote and re-initialize",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether a newer version is available",
    )

    args = parser.parse_args()

    print(f"\n{BOLD}i18n-agent-skill Installer{NC}")
    print("=" * 40)

    if args.check:
        check_for_update()
        return

    if args.update:
        check_git_repo()
        do_update()

    elif args.dev:
        check_git_repo()
        do_dev(workspace=args.workspace)
        setup_venv()

    elif args.link_platforms:
        do_link_platforms()

    else:
        # Default: post-clone setup
        check_git_repo()
        setup_venv()
        patch_gitignore()
        generate_command_proxy()

    print(f"\n{GREEN}{BOLD}Done!{NC}")
    print(f"Activate the skill: {BOLD}/i18n-agent-skill{NC} in your AI assistant.\n")


if __name__ == "__main__":
    main()
