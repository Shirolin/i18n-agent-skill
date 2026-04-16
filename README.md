# i18n-agent-skill 🌐

[![Runtime: Python 3.10+](https://img.shields.io/badge/Runtime-Python%203.10%2B-blue)](https://www.python.org/)
[![Framework: Google ADK](https://img.shields.io/badge/Framework-Google%20ADK-blue)](https://github.com/google/adk)
[![Protocol: MCP](https://img.shields.io/badge/Protocol-MCP-orange)](https://modelcontextprotocol.io)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**i18n-agent-skill** 是一个基于 AI 的前端国际化（i18n）全链路自动化工具。支持硬编码字符串提取、本地隐私脱敏、多语言翻译同步及质量回归检测，旨在提升 React/Vue 等项目的国际化工程化效率。

---

## 🚀 集成与安装 (Setup)

### 1. 快速赋能 (推荐)
直接将本项目 GitHub 链接发送给你的 AI 助手（如 **Cursor, Windsurf, Gemini CLI, Claude**），并指令它：
> **“帮我安装这个 i18n 技能：https://github.com/Shirolin/i18n-agent-skill”**

AI 助手将自动根据你的环境完成配置。这是最省心、也是最推荐的集成方式。

### 2. 标准集成规范
如果需要手动引导 AI 或执行特定安装逻辑，请参考以下规范：

- **Gemini CLI**: 执行 `gemini skill install https://github.com/Shirolin/i18n-agent-skill`。
- **IDE MCP 配置**: 集成命令为 `python -m i18n_agent_skill`。添加为 MCP 服务器后，AI 助手即可获得扫描与翻译能力。

### 3. 开发者本地模式
```bash
pip install -e .
python examples/basic_usage.py
```

---

## 📖 使用指南 (Usage)

本工具支持意图驱动的自动化编排。常用指令示例：

- **项目改造**: `"使用 i18n-agent-skill 国际化改造此项目。"`
  - *流程：目录感知 -> 硬编码提取 -> 翻译包同步 -> 源码重构。*
- **质量审计**: `"对项目进行全量 i18n 审计并修复缺失翻译。"`
  - *流程：缺失检测 -> 风格校验 -> 增量修复。*
- **增量同步**: `"同步当前 Git 变动涉及的文案。"`
  - *流程：基于 Hunk 提取 -> 本地脱敏 -> 翻译提案。*

---

## 🛡️ 技术特性 (Core Features)

*   **自动化提取**: 识别源码硬编码，支持与 `locales/*.json` 的增量比对。
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
