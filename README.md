# i18n-agent-skill 🌐 (Imperial Edition)

[![Framework: Google ADK](https://img.shields.io/badge/Framework-Google%20ADK-blue)](https://github.com/google/adk)
[![Governance: Imperial](https://img.shields.io/badge/Governance-Imperial-gold)](#-皇冠级治理特性)
[![Standard: World%20Class%20Skill](https://img.shields.io/badge/Standard-World%20Class%20Skill-brightgreen)](#-设计哲学)

> **i18n-agent-skill** 是一款进化到“皇冠级”形态的企业级 i18n 智能中枢。它不仅支持标准 ADK 与 MCP 协议，更引入了 **PR 级 Hunk 精准提取**、**AI 自动化评审 (LLM-as-a-Judge)** 与 **云原生结构化观测**，专为拥有严苛治理标准的大型科技公司设计。

---

## 🚀 皇冠级治理特性 (Imperial Governance)

本项目现已超越功能工具范畴，迈入“智能治理”时代：

1.  **PR 级 Hunk 精准提取**: 手术刀级别的增量防护。深度解析 Git Diff，仅处理当前 PR 变动行及其附近的文案。在大规模遗留代码库中，这能彻底杜绝因处理全量文件而引入的无关变更风险。
2.  **AI 自动化评审 (LLM-as-a-Judge)**: 翻译质量的“双模型校验”。内置交叉评审机制，对生成的每一条翻译进行 0-10 分的质量审计，确保翻译不仅正确，而且“地道”。
3.  **云原生结构化观测 (Structured JSON Logging)**: 告别凌乱的文本日志。所有执行行为、Telemetry 指标均以标准 JSON 格式输出，可无缝对接 ELK、Datadog 等企业级监控平台。
4.  **全平台 MCP 兼容**: 既是工具，也是服务。原生支持 Claude Desktop、Cursor 一键集成。

---

## 📁 项目结构

```text
i18n-agent-skill/
├── i18n_agent_skill/   
│   ├── logger.py       # [新] 云原生结构化日志配置
│   ├── vcs.py          # [新] Hunk 级 Git 解析引擎
│   ├── __main__.py     # MCP Server 枢纽
│   ├── linter.py       # 文案美学守卫
│   ├── models.py       # 治理级 Pydantic 数据模型
│   └── tools.py        # 具备评审与 Hunk 防护的核心原子工具
└── README.md           
```

---

## 🛠 企业级观测示例

本项目生成的日志可直接被云原生系统解析：
```json
{"timestamp": "2026-04-14T...", "levelname": "INFO", "message": "Strings extracted", "file": "App.tsx", "keys": 2, "duration_ms": 12.5}
```

---

## 🔄 手术刀式提取演示
仅修改文件中的特定行，Agent 将自动忽略其余部分的数千个干扰词条：
-   **操作**: `git diff` 显示修改了第 10 行。
-   **效果**: `scan_file(vcs_mode=True)` 仅返回第 10 行附近的提取结果。

---

## 📄 License
MIT
