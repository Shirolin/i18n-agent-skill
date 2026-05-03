#!/bin/sh
# install-skill.sh — Level 5 Autonomous Installer (Refined UX)
# Fully compliant with Google ADK & agent-skill-creator standards

set -eu

SKILL_NAME="i18n-agent-skill"
VERSION="0.3.0"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# UI Helpers
BLUE='\033[0;34m'; GREEN='\033[0;32m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()    { printf "${BLUE}[INFO]${NC}  %s\n" "$1"; }
success() { printf "${GREEN}[OK]${NC}    %s\n" "$1"; }
error()   { printf "${RED}[ERROR]${NC} %s\n" "$1"; }

# 1. Environment Setup
setup_venv() {
    info "Preparing isolated Python environment..."
    cd "$SCRIPT_DIR"
    
    if ! command -v python3 >/dev/null 2>&1; then
        error "python3 is required but not found."
        exit 1
    fi

    [ ! -d ".venv" ] && python3 -m venv .venv
    
    if [ -f ".venv/bin/python" ]; then
        ./.venv/bin/python -m pip install --upgrade pip --quiet
        ./.venv/bin/python -m pip install -e . --quiet
    else
        error ".venv setup failed."
        exit 1
    fi
    success "Isolated environment ready."
}

# 2. Deployment Modes
deploy_local() {
    TARGET="$SCRIPT_DIR/.agents/skills/$SKILL_NAME"
    info "Installing to local project: $TARGET"
    mkdir -p "$(dirname "$TARGET")"
    [ -e "$TARGET" ] && rm -rf "$TARGET"
    ln -s "$SCRIPT_DIR" "$TARGET" 2>/dev/null || cp -R "$SCRIPT_DIR" "$TARGET"
    success "Local installation complete."
}

deploy_global() {
    MODE=$1 # "copy" or "symlink"
    PATHS="${HOME}/.claude/skills/$SKILL_NAME ${HOME}/.cursor/rules/$SKILL_NAME ${HOME}/.gemini/skills/$SKILL_NAME ${HOME}/.agents/skills/$SKILL_NAME"
    DEPLOY_COUNT=0
    
    for P in $PATHS; do
        PARENT=$(dirname "$P")
        if [ -d "$PARENT" ]; then
            info "Deploying to: $P ($MODE)"
            [ -e "$P" ] && rm -rf "$P"
            if [ "$MODE" = "symlink" ]; then
                ln -s "$SCRIPT_DIR" "$P" 2>/dev/null || cp -R "$SCRIPT_DIR" "$P"
            else
                cp -R "$SCRIPT_DIR" "$P"
            fi
            DEPLOY_COUNT=$((DEPLOY_COUNT + 1))
        fi
    done
    
    if [ $DEPLOY_COUNT -eq 0 ]; then
        UNIVERSAL="${HOME}/.agents/skills/$SKILL_NAME"
        mkdir -p "$(dirname "$UNIVERSAL")"
        cp -R "$SCRIPT_DIR" "$UNIVERSAL"
        info "Deployed to universal path: $UNIVERSAL"
    fi
}

# 3. Interactive Menu
show_menu() {
    # Check if terminal is interactive (Agent-friendly)
    if [ ! -t 0 ]; then
        info "Non-interactive shell detected. Defaulting to: Local Project Only"
        deploy_local
        return
    fi

    printf "\nPlease select installation mode:\n"
    printf "  ${BOLD}[1] Local Project Only${NC}  (Safe: Installs to ./.agents/skills) ${BLUE}[DEFAULT]${NC}\n"
    printf "  ${BOLD}[2] Global Auto-Deploy${NC}  (Copy to detected AI assistants)\n"
    printf "  ${BOLD}[3] Developer Mode${NC}      (Symlink to detected AI assistants)\n"
    printf "\nSelect [1-3] (Press Enter for 1): "
    read -r CHOICE
    case "$CHOICE" in
        2) deploy_global "copy" ;;
        3) deploy_global "symlink" ;;
        *) deploy_local ;;
    esac
}

main() {
    printf "${BOLD}i18n-agent-skill Autonomous Installer${NC} v$VERSION\n"
    printf "========================================\n"
    
    MODE="interactive"
    for arg in "$@"; do
        case $arg in
            --local)  MODE="local" ;;
            --global) MODE="global" ;;
            --dev)    MODE="dev" ;;
        esac
    done

    setup_venv

    case "$MODE" in
        local)  deploy_local ;;
        global) deploy_global "copy" ;;
        dev)    deploy_global "symlink" ;;
        *)      show_menu ;;
    esac

    printf "\n${GREEN}${BOLD}Installation Successful!${NC}\n"
    printf "To activate, type: ${BOLD}/$SKILL_NAME${NC} in your AI assistant.\n"
}

main "$@"
