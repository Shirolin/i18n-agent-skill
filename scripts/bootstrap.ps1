# bootstrap.ps1 — i18n-agent-skill Windows 环境初始化脚本
# 用法：在 Skill 安装目录下执行
#   powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
# 功能：检测 Python、创建 .venv、安装依赖——等价于 install.sh

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillRoot = Split-Path -Parent $ScriptDir
$VenvDir = Join-Path $SkillRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

Write-Host "==> i18n-agent-skill Windows 环境引导程序" -ForegroundColor Cyan

# --- 1. 寻找可用的 Python 3.10+ ---
$PythonBin = $null
foreach ($cmd in @("py", "python3", "python")) {
    try {
        $ver = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($ver -match "^(\d+)\.(\d+)") {
            $major = [int]$Matches[1]; $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 10) {
                $PythonBin = $cmd
                Write-Host "==> 检测到 Python $ver ($cmd)" -ForegroundColor Green
                break
            }
        }
    } catch { }
}

if (-not $PythonBin) {
    Write-Host @"
[ERROR] 未找到 Python 3.10+ 环境。请通过以下方式之一安装：
  1. 官网: https://www.python.org/downloads/
  2. winget: winget install -e --id Python.Python.3.12
  3. Microsoft Store（搜索 Python）
安装后重新运行本脚本。
"@ -ForegroundColor Red
    exit 1
}

# --- 2. 创建或复用 .venv ---
if (Test-Path $VenvPython) {
    Write-Host "==> 虚拟环境已存在，跳过创建。" -ForegroundColor Green
} else {
    Write-Host "==> 正在创建隔离虚拟环境 (.venv)..." -ForegroundColor Cyan
    & $PythonBin -m venv $VenvDir
    Write-Host "==> 虚拟环境创建完成。" -ForegroundColor Green
}

# --- 3. 安装/更新依赖 ---
Write-Host "==> 正在安装项目依赖（可编辑模式）..." -ForegroundColor Cyan
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -e $SkillRoot --quiet
Write-Host "==> 依赖安装完成。" -ForegroundColor Green

# --- 4. 验证安装 ---
Write-Host "`n==> 正在验证安装..." -ForegroundColor Cyan
& $VenvPython -m i18n_agent_skill status

Write-Host @"

恭喜！环境初始化成功。
之后使用本 Skill 时，请用以下路径调用（无需激活 venv）：
  $VenvPython -m i18n_agent_skill status
"@ -ForegroundColor Green
