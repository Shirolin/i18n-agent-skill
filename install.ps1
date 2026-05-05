# install.ps1 — i18n-agent-skill entry point for Windows
#
# This script is a thin PowerShell wrapper. All logic lives in scripts/install.py.
# Run after: git clone --depth 1 https://github.com/Shirolin/i18n-agent-skill <target>
#
# Usage:
#   .\install.ps1                    # Setup Python env (default, post-clone)
#   .\install.ps1 -dev               # Developer: symlink to ~/.agents/skills/
#   .\install.ps1 -update            # Pull updates + re-setup

$ErrorActionPreference = "Stop"

$SkillRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Find-Python {
    foreach ($candidate in "python", "python3") {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) {
            $versionCheck = & $candidate -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        }
    }
    return $null
}

$Python = Find-Python
if (-not $Python) {
    Write-Error "[ERROR] Python 3.8+ is required but not found."
    Write-Host "        Install from https://python.org and re-run."
    exit 1
}

# Pass all arguments to the Python script
& $Python "$SkillRoot\scripts\install.py" $args
