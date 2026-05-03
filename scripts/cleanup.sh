#!/bin/sh
# cleanup.sh — Remove global i18n-agent-skill installations

SKILL_NAME="i18n-agent-skill"

# UI Helpers
BLUE='\033[0;34m'; GREEN='\033[0;32m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info()    { printf "${BLUE}[INFO]${NC}  %s\n" "$1"; }
success() { printf "${GREEN}[OK]${NC}    %s\n" "$1"; }

PATHS="
${HOME}/.claude/skills/$SKILL_NAME
${HOME}/.cursor/rules/$SKILL_NAME
${HOME}/.gemini/skills/$SKILL_NAME
${HOME}/.agents/skills/$SKILL_NAME
"

info "Cleaning up global installations..."

for P in $PATHS; do
    if [ -e "$P" ]; then
        info "Removing: $P"
        rm -rf "$P"
    fi
done

success "Cleanup complete."
