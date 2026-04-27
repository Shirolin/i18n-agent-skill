# bootstrap.ps1 — Level 5 Autonomous Installer (Windows)
# Fully compliant with Google ADK & agent-skill-creator standards

$SKILL_NAME = "i18n-agent-skill"
$VERSION = "0.1.0"
$root_dir = Resolve-Path "$PSScriptRoot\.."

Write-Host "`ni18n-agent-skill Autonomous Installer" -ForegroundColor White -BackgroundColor Black
Write-Host "========================================"

# 1. Isolated Environment Setup
Write-Host "[INFO]  Preparing isolated environment (.venv)..." -ForegroundColor Cyan
Set-Location $root_dir

if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found. Please install Python 3.10+ from python.org."
    exit 1
}

if (!(Test-Path ".venv")) {
    python -m venv .venv
}

# Install dependencies into .venv
$venv_python = Join-Path $root_dir ".venv\Scripts\python.exe"
if (!(Test-Path $venv_python)) {
    Write-Error "Failed to create virtual environment."
    exit 1
}
& $venv_python -m pip install --upgrade pip --quiet
& $venv_python -m pip install -e . --quiet
Write-Host "[OK]    Isolated environment ready." -ForegroundColor Green

# 2. Level 5 Detection Sequence
$target_paths = @(
    "$env:USERPROFILE\.claude\skills\$SKILL_NAME",
    "$env:USERPROFILE\.cursor\rules\$SKILL_NAME",
    "$env:USERPROFILE\.gemini\skills\$SKILL_NAME",
    "$env:USERPROFILE\.agents\skills\$SKILL_NAME",
    "$env:USERPROFILE\.codeium\windsurf\rules\$SKILL_NAME",
    "$env:USERPROFILE\.clinerules\$SKILL_NAME",
    "$env:USERPROFILE\.trae\rules\$SKILL_NAME",
    "$env:USERPROFILE\.roo\rules\$SKILL_NAME"
)

$deploy_count = 0
foreach ($p in $target_paths) {
    $parent = Split-Path $p
    if (Test-Path $parent) {
        Write-Host "[INFO]  Deploying to platform path: $p" -ForegroundColor Cyan
        if (Test-Path $p) { Remove-Item $p -Recurse -Force }
        New-Item -ItemType Junction -Path $p -Target $root_dir | Out-Null
        $deploy_count++
    }
}

if ($deploy_count -eq 0) {
    $universal = Join-Path $env:USERPROFILE ".agents\skills\$SKILL_NAME"
    $u_parent = Split-Path $universal
    if (!(Test-Path $u_parent)) { New-Item -ItemType Directory -Path $u_parent -Force }
    if (Test-Path $universal) { Remove-Item $universal -Recurse -Force }
    New-Item -ItemType Junction -Path $universal -Target $root_dir | Out-Null
    Write-Host "[INFO]  Deployed to universal path: $universal" -ForegroundColor Cyan
}

Write-Host "`nInstallation Successful!" -ForegroundColor Green
Write-Host "To activate, type: /$SKILL_NAME in your AI assistant.`n"
