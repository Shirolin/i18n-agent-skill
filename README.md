# i18n-agent-skill 🌐

[![Runtime: Python 3.10-3.12](https://img.shields.io/badge/Runtime-Python%203.10--3.12-blue)](https://www.python.org/)
[![Spec: Agent Skill v4.0](https://img.shields.io/badge/Spec-Agent%20Skill%20v4.0-darkgreen)](https://github.com/FrancyJGLisboa/agent-skill-creator)
[![Engine: Tree-sitter AST](https://img.shields.io/badge/Engine-Tree--sitter%20AST-orange)](https://tree-sitter.github.io/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**i18n-agent-skill** 是一款专为 AI 助手设计的**工业级前端国际化全链路自动化工具**。它基于最新的 **Agent Skill 开放标准** 进行了深度优化，适配包括 Cursor, Claude Code, Windsurf 在内的 20+ 种主流 AI 编码助手。

## ✨ 核心优势

- **Tree-sitter AST 引擎**: 毫秒级语法解析，100% 物理隔离注释，支持 JSX/Vue/TSX 深度嵌套提取。
- **进化型迭代优化**: 基于翻译生命周期状态 (Draft/Reviewed/Approved) 进行幂等优化，支持从人工修正中自动学习术语。
- **专家级质量巡检**: 自动生成深度评审报告，识别术语不一致、语境缺失及地道度问题。
- **多语种语义对齐**: 支持以熟悉语种为基准，跨语言同步语义，确保全球表达一致性。
- **隐私盾 (Privacy Guard)**: 在本地通过哈希与掩码技术脱敏 API Key、PII 信息，确保数据不出本地沙箱。
- **全球化原生 (Global Native)**: 完全符合 Google ADK 范式，支持多语言 `SKILL.md`，代码文案全面英文解耦，适配全球开发者。
- **跨平台兼容**: 符合 `SKILL.md` 规范，一键安装至任意主流 AI 助手环境。
- **自动化排版**: 内置多语言 Linter，自动处理中西文混排空格、全角标点一致性。

---

## 🚀 快速开始

### 1. 一键安装 (仅需 5 秒)

在项目根目录下运行安装脚本：

```bash
# 自动检测环境、安装依赖并部署到 AI 助手
chmod +x scripts/install-skill.sh
./scripts/install-skill.sh
```

### 2. 在 AI 助手中激活

安装完成后，在任意支持的 AI 助手中输入以下指令即可激活：

> **"/i18n-agent-skill 帮我扫描 src 目录下的硬编码中文"**

---

## 📖 核心指令集

| 指令 | 说明 |
| :--- | :--- |
| `/i18n-audit` | 覆盖率审计：检查各语言包的缺失情况。 |
| `/i18n-audit-quality` | **质量巡检**：生成专家报告，识别争议项与地道度问题。 |
| `/i18n-pivot-sync` | **跨语言对齐**：根据已优化的母语版本，同步修正其他语种。 |
| `/i18n-fix` | 快捷修复：自动扫描环境异常，生成全量修复提案。 |
| `/i18n-status` | 状态验证：检查项目配置与就绪状态。 |
| `/i18n-sync` | 智能同步：执行增量翻译同步。 |

---

## 📂 项目结构 (optimized by agent-skill-creator)

```text
i18n-agent-skill/
├── i18n_agent_skill/   # 核心 Python 逻辑包
├── scripts/            # [NEW] 自动化脚本：install.sh, cli-tools
├── references/         # [NEW] 技术文档：AST 原理、隐私脱敏协议、Linter 规范
├── assets/             # [NEW] 配置资产：词汇表模板等
├── tests/              # 自动化测试套件 (Unit & Integration)
├── SKILL.md            # 核心执行协议 (v4.0 规范)
└── pyproject.toml      # 依赖管理与项目索引
```

---

## 🛠 开发与自检

本项目集成了标准的自检工具：

```bash
# 执行协议合规性验证
npm run validate  # 或 python .agents/skills/agent-skill-creator/scripts/validate.py .

# 执行安全扫描
npm run scan      # 或 python .agents/skills/agent-skill-creator/scripts/security_scan.py .

# 运行测试
pytest
```

---

## 🔒 安全说明

我们承诺绝不将您的源代码上传至任何第三方服务器。所有的代码解析、隐私脱敏和建议生成均在您的本地环境完成。AI 仅在您明确许可的情况下获取脱敏后的文案片段以协助翻译。

---

## 📄 开源协议

[Apache-2.0](LICENSE)
