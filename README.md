# i18n-agent-skill 🌐 (Intelligent Collaboration)

[![Framework: Google ADK](https://img.shields.io/badge/Framework-Google%20ADK-blue)](https://github.com/google/adk)
[![Model: Agnostic](https://img.shields.io/badge/Model-Gemini%20|%20Claude%20|%20GPT-green)](https://github.com/google/adk)
[![Standard: Intelligent%20Skill](https://img.shields.io/badge/Standard-Intelligent%20Skill-blue)](#-终极形态进化)

> **i18n-agent-skill** 是一款具备“智慧协作”能力的工业级国际化 Agent 技能。基于 Google ADK 终极范式构建，它引入了 **VCS (Git) 感知**、**交互式提案微调**与**全链路效能追踪**，将 AI 辅助开发的效能推至巅峰。

---

## 🚀 终极进化特性 (Elite Intelligent Features)

本项目已超越大师级标准，迈入“智慧协同”时代：

1.  **VCS (Git) 精准扫描**: 内置 Git 集成。自动定位当前分支已修改的文件，扫描范围从 O(N) 降至 O(1)，即使在数万个文件的超大仓库中也能秒级响应。
2.  **交互式微调循环 (Refinement Loop)**: 提案不再是“非全即无”。支持针对特定词条提供人类反馈（如：“把提案里的 A 改为 B”），Agent 将实现局部精准修正。
3.  **全链路效能看板 (Telemetry)**: 自动打点记录毫秒级耗时、缓存拦截率及 Token 节省指标。用数据证明 AI 的提效价值。
4.  **安全路径沙箱**: 坚决防御目录穿越攻击，确保执行环境绝对隔离。

---

## 📁 项目结构

```text
i18n-agent-skill/
├── SKILL.md            # 终极形态技能定义 (含微调指令)
├── i18n_agent_skill/   
│   ├── models.py       # Pydantic 效能与微调模型
│   ├── tools.py        # 异步驱动核心 (含 VCS 与 Telemetry)
│   └── __init__.py
├── examples/           
│   └── basic_usage.py  # 演示 Git 联动与微调流程
└── README.md           
```

## 🚀 快速开始

### 1. 开启 VCS 加速模式
在 Git 仓库根目录执行，Agent 会自动识别变动：
```bash
# Agent 会在执行时自动输出 Telemetry 数据
python -m examples.basic_usage
```

### 2. 参与微调循环
当 Agent 给出提案 ID 后，你可以通过反馈进行修正：
> "帮我微调提案 ID-xxx，把里面所有的 'Login' 统一翻译为 '立即进入'。"

---

## 🧠 设计哲学 (Design Philosophy)

本项目的终极目标是实现 **“高情商的效能 (Emotional Intelligence & Efficiency)”**：
- **VCS** 追求极致的速度。
- **Refinement** 追求完美的人机契合度。
- **Telemetry** 追求透明的量化指标。

---

## 📄 License
MIT
