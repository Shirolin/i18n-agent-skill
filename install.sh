#!/bin/sh
# install.sh — i18n-agent-skill entry point
#
# This script is a thin POSIX shell wrapper. All logic lives in scripts/install.py.
# Run after: git clone --depth 1 https://github.com/Shirolin/i18n-agent-skill <target>
#
# Usage:
#   ./install.sh                    # Setup Python env (default, post-clone)
#   ./install.sh --dev              # Developer: symlink to ~/.agents/skills/
#   ./install.sh --dev --workspace  # Developer: also symlink to CWD/.agents/skills/
#   ./install.sh --link-platforms   # Create optional platform symlinks
#   ./install.sh --update           # Pull updates + re-setup
#   ./install.sh --check            # Check for available updates

set -e

SKILL_ROOT="$(cd "$(dirname "$0")" && pwd)"

# Locate a Python 3.8+ interpreter
find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" -c \
               "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" \
               2>/dev/null; then
                echo "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON=$(find_python) || {
    echo "[ERROR] Python 3.8+ is required but not found."
    echo "        Install from https://python.org and re-run."
    exit 1
}

exec "$PYTHON" "$SKILL_ROOT/scripts/install.py" "$@"
