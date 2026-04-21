# bootstrap.ps1 — i18n-agent-skill Windows env setup
# Usage: powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1

$ErrorActionPreference = 'Stop'
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillRoot  = Split-Path -Parent $ScriptDir
$VenvDir    = Join-Path $SkillRoot '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'

Write-Host '==> i18n-agent-skill Windows bootstrap' -ForegroundColor Cyan

# --- 1. Find Python 3.10+ ---
$PythonBin = $null
foreach ($cmd in 'py', 'python3', 'python') {
    try {
        $ver = & $cmd --version 2>&1  # outputs: "Python 3.10.11"
        if ($ver -match '^Python (\d+)\.(\d+)') {
            if ([int]$Matches[1] -ge 3 -and [int]$Matches[2] -ge 10) {
                $PythonBin = $cmd
                Write-Host ('==> Found ' + $ver + ' (' + $cmd + ')') -ForegroundColor Green
                break
            }
        }
    } catch { }
}

if (-not $PythonBin) {
    Write-Host '[ERROR] Python 3.10+ not found. Install via:' -ForegroundColor Red
    Write-Host '  1. https://www.python.org/downloads/' -ForegroundColor Red
    Write-Host '  2. winget install -e --id Python.Python.3.12' -ForegroundColor Red
    Write-Host '  3. Microsoft Store -> search Python' -ForegroundColor Red
    exit 1
}

# --- 2. Create .venv ---
if (Test-Path $VenvPython) {
    Write-Host '==> .venv already exists, skipping.' -ForegroundColor Green
} else {
    Write-Host '==> Creating .venv ...' -ForegroundColor Cyan
    & $PythonBin -m venv $VenvDir
    Write-Host '==> .venv created.' -ForegroundColor Green
}

# --- 3. Install dependencies ---
Write-Host '==> Installing dependencies (editable mode) ...' -ForegroundColor Cyan
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -e $SkillRoot --quiet
Write-Host '==> Done.' -ForegroundColor Green

# --- 4. Verify ---
Write-Host '==> Verifying install ...' -ForegroundColor Cyan
& $VenvPython -m i18n_agent_skill status

Write-Host ''
Write-Host '==> Bootstrap complete!' -ForegroundColor Green
Write-Host ('==> Use this Python to invoke the skill (no activation needed):') -ForegroundColor Green
Write-Host ('     ' + $VenvPython + ' -m i18n_agent_skill <command>') -ForegroundColor Green
