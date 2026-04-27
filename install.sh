#!/bin/sh
# Entry point for i18n-agent-skill installation

if [ "$(uname)" = "Darwin" ] || [ "$(uname)" = "Linux" ]; then
    chmod +x scripts/install-skill.sh
    ./scripts/install-skill.sh "$@"
elif [ "$(expr substr $(uname -s) 1 5)" = "Linux" ]; then
    chmod +x scripts/install-skill.sh
    ./scripts/install-skill.sh "$@"
else
    # Fallback to PowerShell for Windows CMD/Git Bash
    powershell.exe -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
fi
