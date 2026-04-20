#!/bin/sh
# install-skill.sh — i18n-agent-skill 跨平台安装脚本
# 由 agent-skill-creator 优化生成

set -eu

SKILL_NAME="i18n-agent-skill"
VERSION="0.1.0"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 颜色定义
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; NC=''
fi

info()    { printf "${BLUE}[INFO]${NC}  %s\n" "$1"; }
success() { printf "${GREEN}[OK]${NC}    %s\n" "$1"; }
warn()    { printf "${YELLOW}[WARN]${NC}  %s\n" "$1"; }
error()   { printf "${RED}[ERROR]${NC} %s\n" "$1" >&2; }

# ---------------------------------------------------------------------------
# 1. 环境验证
# ---------------------------------------------------------------------------
check_env() {
    info "正在检查 Python 环境..."
    if ! command -v python3 >/dev/null 2>&1; then
        error "未找到 python3。请先安装 Python 3.10+。"
        exit 1
    fi
    py_ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    info "检测到 Python $py_ver"
    
    # 简单的版本比较 (>=3.10)
    if [ "$(printf '%s\n' "3.10" "$py_ver" | sort -V | head -n1)" != "3.10" ]; then
        error "Python 版本过低，需要 3.10 或更高版本。"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# 2. 安装依赖
# ---------------------------------------------------------------------------
install_deps() {
    info "正在安装/更新项目依赖..."
    # 切换回项目根目录（相对于 scripts 目录的上一级）
    cd "$SCRIPT_DIR"
    if [ -f "pyproject.toml" ]; then
        python3 -m pip install -e . --quiet
        success "依赖安装完成 (Editable mode)"
    else
        error "未找到 pyproject.toml，无法安装依赖。"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# 3. 平台检测与放置 (简化版)
# ---------------------------------------------------------------------------
PLACE_PATH=""
detect_platform() {
    if [ -d "${HOME}/.claude" ]; then PLACE_PATH="${HOME}/.claude/skills/$SKILL_NAME"; fi
    if [ -d "${HOME}/.cursor" ]; then PLACE_PATH="${HOME}/.cursor/rules/$SKILL_NAME"; fi
    if [ -z "$PLACE_PATH" ]; then
        # 兜底：通用路径
        PLACE_PATH="${HOME}/.agents/skills/$SKILL_NAME"
    fi
}

deploy_skill() {
    info "正在部署技能到: $PLACE_PATH"
    mkdir -p "$(dirname "$PLACE_PATH")"
    
    # 建立软链接或复制
    if [ -e "$PLACE_PATH" ]; then rm -rf "$PLACE_PATH"; fi
    
    # 我们倾向于软链接，这样代码修改能立即生效
    if ln -s "$SCRIPT_DIR" "$PLACE_PATH" 2>/dev/null; then
        success "已创建软链接部署。"
    else
        cp -R "$SCRIPT_DIR" "$PLACE_PATH"
        success "已执行物理复制部署。"
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    printf "${BOLD}i18n-agent-skill 安装程序 (v${VERSION})${NC}\n"
    printf "========================================\n"
    
    check_env
    install_deps
    detect_platform
    deploy_skill
    
    printf "\n${GREEN}${BOLD}安装成功！${NC}\n"
    printf "现在你可以通过在对话中输入 ${BOLD}/i18n-agent-skill${NC} 来激活本引擎。\n"
    printf "运行 ${BOLD}python -m i18n_agent_skill status${NC} 验证安装状态。\n"
}

main "$@"
