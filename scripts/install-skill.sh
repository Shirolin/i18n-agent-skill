#!/bin/sh
# install-skill.sh — Level 5 Autonomous Installer
# Fully compliant with Google ADK & agent-skill-creator standards

set -eu

SKILL_NAME="i18n-agent-skill"
VERSION="0.1.0"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# UI Helpers
BLUE='\033[0;34m'; GREEN='\033[0;32m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()    { printf "${BLUE}[INFO]${NC}  %s\n" "$1"; }
success() { printf "${GREEN}[OK]${NC}    %s\n" "$1"; }

# 1. Environment Setup (Isolated .venv)
setup_venv() {
    info "Preparing isolated Python environment..."
    cd "$SCRIPT_DIR"
    
    if ! command -v python3 >/dev/null 2>&1; then
        error "python3 is required but not found. Please install Python 3.10+."
        exit 1
    fi

    if [ ! -d ".venv" ]; then
        if ! python3 -m venv .venv 2>/dev/null; then
            error "Failed to create virtual environment. If you are on Ubuntu/Debian, try: sudo apt install python3-venv"
            exit 1
        fi
    fi
    
    # Install dependencies inside venv
    if [ "$(uname)" = "Darwin" ] || [ "$(uname)" = "Linux" ]; then
        if [ ! -f ".venv/bin/python" ]; then
            error ".venv/bin/python not found. Virtual environment creation may have failed."
            exit 1
        fi
        ./.venv/bin/python -m pip install --upgrade pip --quiet
        ./.venv/bin/python -m pip install -e . --quiet
    fi
    success "Isolated environment ready."
}

# 2. Multi-Platform Detection (Level 5 Sequence)
deploy_skill() {
    # Sequence based on agent-skill-creator best practices
    PATHS="
    ${HOME}/.claude/skills/$SKILL_NAME
    ${HOME}/.cursor/rules/$SKILL_NAME
    ${HOME}/.gemini/skills/$SKILL_NAME
    ${HOME}/.agents/skills/$SKILL_NAME
    ${HOME}/.codeium/windsurf/rules/$SKILL_NAME
    ${HOME}/.clinerules/$SKILL_NAME
    ${HOME}/.trae/rules/$SKILL_NAME
    ${HOME}/.roo/rules/$SKILL_NAME
    "
    
    DEPLOY_COUNT=0
    for P in $PATHS; do
        # Try to detect if the platform exists
        PARENT=$(dirname "$P")
        if [ -d "$PARENT" ]; then
            info "Deploying to platform path: $P"
            mkdir -p "$PARENT"
            [ -e "$P" ] && rm -rf "$P"
            
            # Create symlink for live updates
            if ln -s "$SCRIPT_DIR" "$P" 2>/dev/null; then
                DEPLOY_COUNT=$((DEPLOY_COUNT + 1))
            else
                cp -R "$SCRIPT_DIR" "$P"
                DEPLOY_COUNT=$((DEPLOY_COUNT + 1))
            fi
        fi
    done
    
    if [ $DEPLOY_COUNT -eq 0 ]; then
        # Universal fallback
        UNIVERSAL="${HOME}/.agents/skills/$SKILL_NAME"
        mkdir -p "$(dirname "$UNIVERSAL")"
        ln -s "$SCRIPT_DIR" "$UNIVERSAL" 2>/dev/null || cp -R "$SCRIPT_DIR" "$UNIVERSAL"
        info "Deployed to universal path: $UNIVERSAL"
    fi
}

main() {
    printf "${BOLD}i18n-agent-skill Autonomous Installer${NC}\n"
    printf "========================================\n"
    setup_venv
    deploy_skill
    printf "\n${GREEN}${BOLD}Installation Successful!${NC}\n"
    printf "To activate, type: ${BOLD}/$SKILL_NAME${NC} in your AI assistant.\n"
}

main "$@"
