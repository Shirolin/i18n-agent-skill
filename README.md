# i18n-agent-skill 🌐

[![Runtime: Python 3.9+](https://img.shields.io/badge/Runtime-Python%203.9%2B-blue)](https://www.python.org/)
[![Framework: Google ADK](https://img.shields.io/badge/Framework-Google%20ADK-blue)](https://github.com/google/adk)
[![Protocol: MCP](https://img.shields.io/badge/Protocol-MCP-orange)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**i18n-agent-skill** 是一款专为前端工程（React, Vue 等）设计的 **软件国际化（i18n）自动化工具**。它能自动从源码中提取硬编码字符串，在本地完成隐私脱敏后，由 AI 自动生成翻译并同步至项目语言包（JSON），实现从开发到多语言发布的工程闭环。

---

## 🚀 快速集成 (Quick Start)

### 1. 自然语言安装 (推荐)
直接将本项目 GitHub 链接粘贴给你的 AI 助手（如 Cursor, Gemini CLI, Claude），并发送指令：
> **“安装这个技能：https://github.com/Shirolin/i18n-agent-skill”**

AI 助手将自动识别并完成配置。

### 2. 标准集成规范 (面向 AI 与高级用户)
如果需要手动配置或引导 AI 执行特定安装逻辑，请参考以下规范：

*   **Gemini CLI**:
    ```bash
    gemini skill install https://github.com/Shirolin/i18n-agent-skill
    ```
*   **IDE (Cursor/VS Code/Claude) - MCP 配置**:
    - **运行时**: Python 3.9+
    - **集成命令**: `python -m i18n_agent_skill`
    - **说明**: 将此命令添加为 MCP 服务器，AI 助手即可获得扫描源码并同步翻译的能力。

---

## 📖 使用指南 (Usage Guide)

一旦集成完成，你只需通过自然语言指挥 AI 助手即可触发底层自动化逻辑：

### 核心指令示例 (Example Prompts)
- **项目预检**: `"查看当前项目的 i18n 状态和 Git 变动。"` -> 自动触发 `get_status`。
- **增量同步**: `"扫描 src 目录下新增的文案，并同步到中、英文翻译包。"` -> 自动触发 `scan_file` (VCS 模式) + `propose_sync`。
- **补全缺失**: `"找出 ja.json 中缺失的条目，参考英文原件进行补全。"` -> 自动触发 `get_missing_keys` + `propose_sync`。
- **术语管理**: `"将 'Submit' 翻译为 '确认提交' 存入术语表。"` -> 自动触发 `learn_term`。
- **安全提交**: `"确认并提交 ID 为 [proposal_id] 的翻译提案。"` -> 自动触发 `commit_changes`。

---

## 🔑 关于 API Key (核心说明)

| 场景 | 是否需要配置 API Key | 说明 |
| :--- | :--- | :--- |
| **本地提取/扫描/检查** | ❌ **不需要** | 纯本地 Python 逻辑。 |
| **通过 IDE (Cursor/Claude) 调用** | ❌ **不需要** | **推荐。** 直接复用 IDE 自身的 AI 额度。 |
| **通过 Gemini CLI 调用** | ❌ **不需要** | **推荐。** 复用 CLI 宿主环境的授权。 |
| **手动运行 Python 翻译脚本** | ✅ **需要** | 仅当你直接运行代码且需要 AI 生成翻译时。 |

---

## ✨ 核心特性

*   **🔍 自动化提取与同步**: 自动识别源码硬编码，并与 `locales/*.json` 进行增量比对。
*   **🛡️ 本地隐私脱敏**: 文案外发前自动本地识别并屏蔽 API Key、Email、Token 等。
*   **🌿 VCS 增量感知**: 基于 `git diff` 实现 Hunk 级精准提取，仅处理变动行。
*   **📈 质量回归检测**: 自动对比历史翻译得分，拦截任何质量退化的翻译结果。

---

## ⚙️ 配置参考 (Optional)

本工具默认支持 **零配置启动**（自动探测 `src/` 与 `locales/`）。
如需覆盖默认逻辑，请在根目录创建 `.i18n-skill.json`：
```json
{
  "source_dirs": ["src"],
  "locales_dir": "locales",
  "privacy_level": "basic",
  "enabled_langs": ["en", "zh-CN"]
}
```

---

## 📄 License
MIT
