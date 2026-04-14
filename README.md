# i18n-agent-skill 🌐 (Industrial Grade)

[![Framework: Google ADK](https://img.shields.io/badge/Framework-Google%20ADK-blue)](https://github.com/google/adk)
[![Model: Agnostic](https://img.shields.io/badge/Model-Gemini%20|%20Claude%20|%20GPT-green)](https://github.com/google/adk)
[![Standard: Industrial%20Grade%20Skill](https://img.shields.io/badge/Standard-Industrial%20Grade%20Skill-red)](#-工业化配置与预检)

> 极致工业化的 AI 国际化工具集。基于 Google ADK 工业化范式构建，具备项目契约感知、自动化预检与安全沙箱加固。

---

## 🚀 工业化特性 (Industrial Features)

本项目现已全面升级至工业级标准，专为大型复杂工程设计：

1.  **项目契约配置 (`.i18n-skill.json`)**: 引入显式配置机制。通过契约明确定义源码目录、忽略规则及语言清单，消除 AI 对环境的盲目猜测。
2.  **自动化预检工具 (`Pre-flight Check`)**: 新增 `check_project_status` 工具。Agent 在开工前会进行自我诊断，确保环境、权限及配置完全就绪。
3.  **语义化描述优化 (Rich Metadata)**: 所有工具接口均经过 Prompt 工程化重写。描述中包含“最佳实践”与“行为边界”，最大限度降低小参数模型的执行抖动。
4.  **安全路径沙箱**: 所有的文件读写被物理锁定在工作空间内，坚决防御目录穿越攻击。

---

## 📁 目录结构

```text
i18n-agent-skill/
├── .i18n-skill.json    # 项目契约配置文件 (示例)
├── SKILL.md            # 工业化技能定义 (包含预检指令)
├── i18n_agent_skill/   
│   ├── models.py       # 经过 Prompt 工程化优化的 Pydantic 模型
│   ├── tools.py        # 包含预检与沙箱逻辑的异步核心
│   └── __init__.py
├── GLOSSARY.json       # 项目专属术语表
├── examples/           
│   └── basic_usage.py  # 演示预检与自纠错工作流
└── README.md           
```

## 🚀 快速开始

### 1. 初始化项目契约
在项目根目录创建 `.i18n-skill.json`：
```json
{
  "source_dirs": ["src/components"],
  "ignore_dirs": ["node_modules", "tests"],
  "locales_dir": "locales"
}
```

### 2. 启动预检工作流
Agent 会自动调用 `check_project_status` 开始任务。

---

## 🧠 设计哲学 (Design Philosophy)

本项目的目标是实现**“可预测的自治”**：
- **Contract** 建立确定性边界。
- **Pre-flight** 确保执行环境安全。
- **Self-Correction** 保证输出结果的高质量。

---

## 📄 License
MIT
