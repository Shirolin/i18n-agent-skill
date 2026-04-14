# i18n-agent-skill 🌐 (Sovereign Edition)

[![Framework: Google ADK](https://img.shields.io/badge/Framework-Google%20ADK-blue)](https://github.com/google/adk)
[![Governance: Sovereign](https://img.shields.io/badge/Governance-Sovereign-purple)](#-主权级加固特性)
[![Safety: Sandboxed](https://img.shields.io/badge/Safety-Sandboxed-red)](README.md)

> **i18n-agent-skill** 是一款进化到“主权级”形态的企业级国际化智能中枢。它不仅支持极致的工程治理，更引入了 **隐私护盾 (Privacy Shield)** 与 **快照回归 (Snapshot Regression)**，满足金融、医疗等行业对数据主权与资产稳定性的终极苛求。

---

## 🚀 主权级加固特性 (Sovereign Governance)

本项目现已站在 Agent 技能开发的巅峰，具备守护企业核心资产的能力：

1.  **隐私护盾 (Privacy Shield)**: 自动敏感信息脱敏。内置启发式脱敏引擎，在将文案发送至外部大模型前，自动对 API Key、邮箱、Token 等进行掩码处理（如 `[MASKED_API_KEY]`），确保合规性。
2.  **质量快照回归 (Snapshot Regression)**: 语言资产水位线。系统自动记录历史上得分最高（最地道）的翻译。当新模型或新上下文导致翻译质量退化时，自动触发 `regression_alert` 告警。
3.  **PR 级 Hunk 精准提取**: 手术刀级别的增量防护。仅处理当前分支真正变动的代码行，将大文件处理的风险降至零。
4.  **云原生结构化观测**: 全量导出 JSON 格式日志，支持企业级全链路追踪。

---

## 📁 项目结构

```text
i18n-agent-skill/
├── i18n_agent_skill/   
│   ├── snapshot.py     # [新] 主权级快照回归管理器
│   ├── logger.py       # 企业级结构化日志
│   ├── vcs.py          # Hunk 级解析引擎
│   ├── prompts.py      # 指令管理工厂
│   ├── models.py       # Pydantic 主权级数据模型
│   └── tools.py        # 集成隐私护盾的核心工具
└── README.md           
```

---

## 🛠 隐私护盾演示

工具会自动识别代码中的敏感字符串并替换：
-   **源码**: `const apiKey = "sk-1234567890abcdef";`
-   **提取结果**: `{"text": "[MASKED_API_KEY]", "is_masked": true}`
-   **价值**: 保护企业密钥不流入外部 AI 训练集。

---

## 🔄 质量回归保护
系统会自动拦截“退化”的翻译提议：
-   **快照**: `"Submit"` -> `"立即提交"` (得分: 10)
-   **新模型提议**: `"Submit"` -> `"确定"` (得分: 7)
-   **动作**: 系统抛出警告并建议 Agent 重新审视决策。

---

## 📄 License
MIT
