# i18n-agent-skill 🌐

[![Runtime: Python 3.10-3.12](https://img.shields.io/badge/Runtime-Python%203.10--3.12-blue)](https://www.python.org/)
[![Framework: Google ADK](https://img.shields.io/badge/Framework-Google%20ADK-blue)](https://github.com/google/adk)
[![Protocol: MCP](https://img.shields.io/badge/Protocol-MCP-orange)](https://modelcontextprotocol.io)
[![Engine: Tree-sitter AST](https://img.shields.io/badge/Engine-Tree--sitter%20AST-orange)](https://tree-sitter.github.io/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**i18n-agent-skill** 是一款专为 AI 助手（Agent）设计的**工业级前端国际化全链路自动化工具**。它不仅涵盖了从源码重构、隐私审计到翻译同步的完整交付闭环，更通过进化至 **Tree-sitter AST** 解析引擎，大幅提升了在复杂前端项目中的自动化精度与数据安全性。本工具将为以下核心场景提供底层支持：
- **全自动重构**: 闭环处理 React/Vue 遗留项目的国际化改造，实现生产级的代码无损重写。
- **数据隐私盾**: 在 Agent 调用 LLM 前执行本地语法级扫描，确保 API Key 等机密信息不离开物理沙箱。
- **增量同步流**: 结合 Git Hunk 与语法树感知，实现多语言包与业务逻辑的精准增量对齐。
- **质量实验室**: 自动化执行多语言排版规范校验（如空格、标点一致性）及翻译质量的回归检查。

---

## 🚀 集成与安装 (Setup)

### 1. 自动集成 (推荐)
直接将本项目 GitHub 链接发送给你的 AI 助手（无论是 IDE 插件还是命令行 Agent），并发送如下指令：
> **“请安装并配置此 i18n 技能：https://github.com/Shirolin/i18n-agent-skill”**

AI 助手将根据协议规范自动执行依赖安装、环境感知与功能配置。

#### 环境与协议兼容性 (2026.04)
本工具基于 **MCP** 与 **Google ADK** 标准构建，旨在兼容各类现代 AI 助手：
- **核心适配**: Cursor, Gemini CLI, VS Code (Roo Code / Cline)
- **理论支持**: Claude Code, Codex, Windsurf 等支持标准 MCP 协议的环境


### 2. 标准集成规范 (面向 AI 读取)
若需手动引导 AI 或执行特定逻辑，可参考以下标准化参数：
- **Entry Command**: `python -m i18n_agent_skill`
- **Gemini CLI**: `gemini skill install https://github.com/Shirolin/i18n-agent-skill`

### 3. 本地开发模式
```bash
pip install -e ".[dev]"
python examples/basic_usage.py
```

---

## 📖 使用指南 (Usage)

本工具专为以下核心业务场景设计，你只需向 AI 助手发送对应指令：

### 场景 A：首次国际化改造 (Legacy Refactor)
**痛点**: 项目里全是硬编码，想一次性抽离翻译。
> **指令**: `/i18n-refactor` 或 **“帮我把这个老项目做一下国际化改造”**
> *自动化闭环：探测路径 -> 全量提取 -> 生成翻译包 -> 自动重构源码。*

### 场景 B：日常开发同步 (Dev Sync)
**痛点**: 刚写完新功能，想把改动到的文案同步到多语言。
> **指令**: `/i18n-sync` 或 **“同步一下我刚才改动的文案”**
> *自动化闭环：基于 Git Hunk 提取 -> 隐私脱敏 -> 生成增量翻译提案。*

### 场景 C：翻译体检与修复 (Audit & Fix)
**痛点**: 怀疑有漏翻译的 Key，或者想统一多语言排版格式。
> **指令**: `/i18n-fix` 或 **“检查一下项目里有没有漏掉的翻译并修复”**
> *自动化闭环：缺失检测 -> 多语言排版 Linter -> 自动化补全修复。*

---

## 🛡️ 技术特性 (Core Features)

*   **自动化提取**: 基于 **Tree-sitter AST** 实现像素级源码感知，精准识别硬编码文案，并支持增量比对。
*   **本地隐私脱敏**: 文案外传前，自动在本地识别并掩码 API Key、Email、Token 等。
*   **VCS 增量感知**: 底层调用 `git diff` 提取变动行号（Hunks），优化 Token 消耗。
*   **质量回归检测**: 自动对比历史翻译得分，对质量下降的翻译结果触发拦截。

---

## ⚙️ 配置说明 (Optional)

默认支持零配置启动。如需覆盖默认逻辑，可在根目录创建 `.i18n-skill.json`：
```json
{
  "source_dirs": ["src"],
  "locales_dir": "locales",
  "privacy_level": "basic",
  "enabled_langs": ["en", "zh-CN"]
}
```

---

## 🔑 关于 API Key (核心说明)

本项目在集成环境下追求 **“无感授权”** 体验。

| 使用场景 | 是否需要配 Key | 核心说明 |
| :--- | :--- | :--- |
| **本地提取/扫描/脱敏** | ❌ **不需要** | `scan_file`, `get_status` 等本地逻辑完全离线运行。 |
| **通过 Gemini CLI 调用** | ❌ **不需要** | **推荐。** 技能会自动复用 CLI 宿主环境已有的 API 授权。 |
| **在 Cursor/Claude 中使用** | ❌ **不需要** | **推荐。** 技能作为 MCP 工具，直接利用 IDE 的 AI 能力。 |
| **手动运行 Python 脚本** | ✅ **需要** | 仅当你直接运行代码且需要 AI 生成翻译提案时。 |

> **提示**: 在大多数 AI 驱动的工作流中，你完全无需担心 API Key 的配置问题。

---

## 📂 项目结构 (Structure)

```text
i18n-agent-skill/
├── i18n_agent_skill/   # 核心引擎源码包
├── examples/           # 自动化工作流示例
├── tests/              # 单元与集成测试套件
├── SKILL.md            # Agent 执行协议规范
├── .i18n-skill.json    # [可选] 项目配置覆盖
└── pyproject.toml      # 依赖管理与项目元数据
```

---


## 🛠 本地开发 (Development)

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行单元与集成测试
python -m pytest

# 执行静态检查
ruff check .
mypy .
```

---

## 📄 License
Apache-2.0
