# Changelog 📜

所有关于 **i18n-agent-skill** 的重大变更都将记录在此文件中。本项目严格遵循 [语义化版本 (SemVer)](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2026-04-14
### 🚀 初始构建与工程化
- **项目初始化**: 基于 Google ADK 范式构建核心架构。
- **模块化包结构**: 将脚本重构为标准 Python 包 `i18n_agent_skill`。
- **开源合规**: 添加 MIT 协议、`.gitignore` 与现代化的 `pyproject.toml` 配置。

### 💎 核心引擎增强 (Production-Ready)
- **嵌套 JSON 支持**: 引入递归拍平 (Flatten) 与还原算法，完美支持多层级 i18n 字典。
- **Git 冲突防御**: 强制执行有序 JSON 写入，确保多人协作时的版本确定性。
- **工业级容错**: 增加对 JSON 损坏及二进制文件的防御性捕获，杜绝工作流崩溃。
- **高精度提取**: 增强正则表达式捕获能力，支持捕获包含标点与数字的长文本。

### 🌟 大师级范式进化 (Advanced Features)
- **语义上下文感知 (RAG-lite)**: 提取阶段附带源码行号及上下文代码片段，辅助 AI 精准识别语义。
- **增量哈希扫描**: 引入 `.i18n-cache.json` 机制，实现秒级增量提取，极大节省 LLM Token。
- **双阶段提交 (HITL)**: 确立 `Propose -> Review -> Commit` 协议，引入人类审查环节。
- **强类型校验 (Pydantic)**: 使用强类型模型约束所有工具入参，锁死大模型执行幻觉。

### 🛡️ 安全与自纠错加固 (Security & Robustness)
- **安全沙箱 (Sandboxing)**: 内置 Workspace 拦截器，物理锁定读写范围，防御目录穿越攻击。
- **自纠错闭环 (Self-Correction)**: 实现占位符校验失败后的结构化反馈，引导 Agent 自动修正并重试。
- **存储策略抽象**: 解耦逻辑与文件格式，为未来支持 YAML/PO 等格式打下架构基础。

### 👑 皇冠级治理与智慧 (Imperial Governance)
- **PR 级精准防护 (Hunk-Level)**: 深度集成 Git Diff，仅处理真正发生变更的行号区间，实现手术刀级精准提取。
- **云原生观测性**: 引入 JSON 结构化日志与 Telemetry 自动打点，支持企业级监控。
- **风格守卫 (Style Linter)**: 自动化校验中英混排空格（盘古之白）与标点符号规范。
- **AI 自动化评审**: 内置 LLM-as-a-Judge 插槽，实现翻译质量的二次审计与打分。

### 🌌 生态化与终极封顶 (Universal Ecosystem)
- **MCP 全平台支持**: 升级为标准 MCP Server，原生兼容 Claude Desktop、Cursor、Zed。
- **资源挂载 (MCP Resources)**: 动态暴露术语表与翻译库，赋予 AI 实时全局视野。
- **提示词工厂 (Prompt Manager)**: 实现指令的版本化集中管理，轻松适配不同大模型。
- **进化型记忆**: 支持通过微调反馈自动同步 `GLOSSARY.json`，实现术语库自治生长。
- **CI/CD 流水线**: 部署 GitHub Actions 自动化门禁 (Ruff + Mypy + Pytest)。

## [0.2.0] - 2026-04-14
### 🏛️ 主权级架构加固 (Sovereign Tier)
- **隐私护盾 (Privacy Shield)**: 引入启发式脱敏引擎，在发送至外部 LLM 前自动掩码 API Key、邮箱等敏感信息。
- **快照回归系统 (Snapshot Regression)**: 建立 `.i18n-snapshots.json` 资产库，实现翻译质量的“水位线”防护，自动预警翻译退化。
- **治理模型增强**: 扩充 `PrivacyLevel` 与 `RegressionResult` 模型，支持主权级合规审计。
- **全量异步加固**: 进一步优化并发磁盘 I/O 性能。

---
*Generated with ❤️ by Gemini CLI*
