#!/bin/bash

# =================================================================
# i18n-agent-skill Installer
# Supports: Linux, macOS, Windows (Git Bash/MSYS/WSL)
# =================================================================

set -e

# --- 颜色定义 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}==>${NC} 正在准备 i18n-agent-skill 运行环境..."

# --- 1. 操作系统检测 ---
OS_TYPE="$(uname -s)"
case "${OS_TYPE}" in
    Linux*)     PLATFORM=linux;;
    Darwin*)    PLATFORM=macos;;
    MSYS*|MINGW*) PLATFORM=windows;;
    *)          PLATFORM=unknown;;
esac

echo -e "${BLUE}==>${NC} 检测到平台: ${GREEN}${PLATFORM}${NC}"

# --- 2. Python 环境检查 (3.10+) ---
check_python_version() {
    local python_cmd=$1
    if command -v "$python_cmd" >/dev/null 2>&1; then
        local version=$("$python_cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if [ "$(echo "$version >= 3.10" | bc 2>/dev/null || python3 -c "print($version >= 3.10)")" == "True" ]; then
            echo "$python_cmd"
            return 0
        fi
    fi
    return 1
}

PYTHON_BIN=""
for cmd in python3 python python.exe; do
    PYTHON_BIN=$(check_python_version "$cmd")
    if [ -n "$PYTHON_BIN" ]; then break; fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}错误: 未找到 Python 3.10+ 环境。${NC}"
    echo "请安装 Python 3.10 - 3.12 后再试。"
    exit 1
fi

echo -e "${BLUE}==>${NC} 使用 Python: ${GREEN}$($PYTHON_BIN --version)${NC}"

# --- 3. 创建虚拟环境 (venv) ---
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${BLUE}==>${NC} 正在创建隔离的虚拟环境 (.venv)..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
else
    echo -e "${BLUE}==>${NC} 虚拟环境已存在，跳过创建。"
fi

# --- 4. 安装/更新依赖 ---
echo -e "${BLUE}==>${NC} 正在安装/更新项目依赖..."

if [ "${PLATFORM}" == "windows" ]; then
    VENV_PIP="./$VENV_DIR/Scripts/pip"
    VENV_PYTHON="./$VENV_DIR/Scripts/python"
else
    VENV_PIP="./$VENV_DIR/bin/pip"
    VENV_PYTHON="./$VENV_DIR/bin/python"
fi

# 确保 pip 是最新的
"$VENV_PIP" install --upgrade pip --quiet

# 安装项目（以可编辑模式）
"$VENV_PIP" install -e . --quiet

echo -e "${GREEN}恭喜！安装成功。${NC}"

# --- 5. 使用引导 ---
echo ""
echo -e "${YELLOW}如何使用 i18n-agent-skill:${NC}"
echo "-------------------------------------------------------"
if [ "${PLATFORM}" == "windows" ]; then
    echo "1. 激活环境: source .venv/Scripts/activate"
else
    echo "1. 激活环境: source .venv/bin/activate"
fi
echo "2. 运行工具: i18n-agent-skill --help"
echo "-------------------------------------------------------"
echo ""
echo "或者直接通过虚拟环境运行而不激活:"
echo "  $VENV_PYTHON -m i18n_agent_skill status"
echo ""
