[CmdletBinding()]
param(
    [switch]$local,
    [switch]$global,
    [switch]$dev
)

# bootstrap.ps1 — Level 5 Autonomous Installer (Refined UX)
# Fully compliant with Google ADK & agent-skill-creator standards

$SKILL_NAME = "i18n-agent-skill"
$VERSION = "0.3.0"
$root_dir = Resolve-Path "$PSScriptRoot\.."

Write-Host "`ni18n-agent-skill Autonomous Installer v$VERSION" -ForegroundColor White -BackgroundColor Black
Write-Host "========================================"

# 1. Isolated Environment Setup
function Setup-Venv {
    Write-Host "[INFO]  Preparing isolated environment (.venv)..." -ForegroundColor Cyan
    Set-Location $root_dir

    if (!(Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Error "Python not found. Please install Python 3.10+ from python.org."
        exit 1
    }

    if (!(Test-Path ".venv")) {
        python -m venv .venv
    }

    $venv_python = Join-Path $root_dir ".venv\Scripts\python.exe"
    if (!(Test-Path $venv_python)) {
        Write-Error "Failed to create virtual environment."
        exit 1
    }
    & $venv_python -m pip install --upgrade pip --quiet
    & $venv_python -m pip install -e . --quiet
    Write-Host "[OK]    Isolated environment ready." -ForegroundColor Green
}

# 2. Deployment Modes
function Deploy-Local {
    $target = Join-Path $root_dir ".agents\skills\$SKILL_NAME"
    Write-Host "[INFO]  Installing to local project: $target" -ForegroundColor Cyan
    $parent = Split-Path $target
    if (!(Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    if (Test-Path $target) { Remove-Item $target -Recurse -Force }
    New-Item -ItemType Junction -Path $target -Target $root_dir | Out-Null
    Write-Host "[OK]    Local installation complete." -ForegroundColor Green
}

function Deploy-Global ($Mode) {
    $target_paths = @(
        "$env:USERPROFILE\.claude\skills\$SKILL_NAME",
        "$env:USERPROFILE\.cursor\rules\$SKILL_NAME",
        "$env:USERPROFILE\.gemini\skills\$SKILL_NAME",
        "$env:USERPROFILE\.agents\skills\$SKILL_NAME"
    )

    $deploy_count = 0
    foreach ($p in $target_paths) {
        $parent = Split-Path $p
        if (Test-Path $parent) {
            Write-Host "[INFO]  Deploying to: $p ($Mode)" -ForegroundColor Cyan
            if (Test-Path $p) { Remove-Item $p -Recurse -Force }
            
            if ($Mode -eq "symlink") {
                New-Item -ItemType Junction -Path $p -Target $root_dir | Out-Null
            } else {
                Copy-Item -Path $root_dir -Destination $p -Recurse -Exclude ".venv", "__pycache__"
            }
            $deploy_count++
        }
    }

    if ($deploy_count -eq 0) {
        $universal = Join-Path $env:USERPROFILE ".agents\skills\$SKILL_NAME"
        $u_parent = Split-Path $universal
        if (!(Test-Path $u_parent)) { New-Item -ItemType Directory -Path $u_parent -Force | Out-Null }
        if (Test-Path $universal) { Remove-Item $universal -Recurse -Force }
        Copy-Item -Path $root_dir -Destination $universal -Recurse -Exclude ".venv", "__pycache__"
        Write-Host "[INFO]  Deployed to universal path: $universal" -ForegroundColor Cyan
    }
}

# 3. Interactive Menu
function Show-Menu {
    # Check if host is interactive (Agent-friendly)
    if (![Environment]::UserInteractive -or $args.Count -gt 0 -or (Get-Variable -Name MyInvocation -ErrorAction SilentlyContinue).Value.ExpectingInput -eq $false) {
        Write-Host "[INFO]  Non-interactive session detected. Defaulting to: Local Project Only" -ForegroundColor Cyan
        Deploy-Local
        return
    }

    Write-Host "`nPlease select installation mode:"
    Write-Host "  [1] Local Project Only  (Safe: Installs to ./.agents/skills) [DEFAULT]" -ForegroundColor White
    Write-Host "  [2] Global Auto-Deploy  (Copy to detected AI assistants)"
    Write-Host "  [3] Developer Mode      (Symlink to detected AI assistants)"
    
    $choice = Read-Host "`nSelect [1-3] (Press Enter for 1)"
    if ($choice -eq "2") { Deploy-Global "copy" }
    elseif ($choice -eq "3") { Deploy-Global "symlink" }
    else { Deploy-Local }
}

# Main Execution
Setup-Venv

if ($local) { Deploy-Local }
elseif ($global) { Deploy-Global "copy" }
elseif ($dev) { Deploy-Global "symlink" }
else { Show-Menu }

Write-Host "`nInstallation Successful!" -ForegroundColor Green
Write-Host "To activate, type: /$SKILL_NAME in your AI assistant.`n"
