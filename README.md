# i18n-agent-skill 🌐

[![Runtime: Python 3.10+](https://img.shields.io/badge/Runtime-Python%203.10%2B-blue)](https://www.python.org/)
[![Framework: Google ADK](https://img.shields.io/badge/Framework-Google%20ADK-blue)](https://github.com/google/adk)
[![Protocol: MCP](https://img.shields.io/badge/Protocol-MCP-orange)](https://modelcontextprotocol.io)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**i18n-agent-skill** 是一个基于 AI 的前端国际化（i18n）全链路自动化工具。支持硬编码字符串提取、本地隐私脱敏、多语言翻译同步及质量回归检测，旨在提升 React/Vue 等项目的国际化工程化效率。

---

## 🚀 集成与安装 (Integrations)

### 1. 自动化集成 (推荐)
将本项目 GitHub 链接提供给 AI 助手（如 Cursor, Gemini CLI, Claude），指令如下：
> “安装此技能：https://github.com/Shirolin/i18n-agent-skill”

AI 助手将根据协议规范自动执行环境感知与配置。

### 2. 标准配置参考
*   **Gemini CLI**:
    ```bash
    gemini skill install https://github.com/Shirolin/i18n-agent-skill
    ```
*   **MCP (Model Context Protocol) 客户端**:
    - **Runtime**: Python 3.10+
    - **Entry Command**: `python -m i18n_agent_skill`
    - **Capability**: 为 AI 助手提供源码扫描、隐私审查与翻译落盘能力。

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

## 🔑 授权与 Key 说明

| 运行环境 | 权限处理逻辑 |
| :--- | :--- |
| **集成环境 (IDE/CLI)** | ❌ **免配置**。直接复用宿主环境的 AI 授权。 |
| **独立运行 (Local)** | ✅ **需配置**。需设置环境变量 `GOOGLE_API_KEY`。 |

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
