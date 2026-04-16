# AI Evolution & Modification Trace 📜

本项目记录了 AI 助手在人类指引下，经历数百轮对话、数千次逻辑修正所达成的工程化成果。每一行代码背后都是一次思维的对齐与迭代。

## 📍 [Phase 4] 协议主权与架构博弈 (Turns 251 - 320+)
**当前阶段：解决“最后一公里”的落地痛点，确立 AI 执行的边界感。**

- **SKILL.md 准入大修 (Iter-315)**: 经历了 3 次安装失败后，定位并修复了 YAML Frontmatter 缺失问题，补全 `name` 和 `description`，通过 Gemini CLI 准入测试。
- **意图导向重构 (Iter-310)**: 摒弃了描述性的术语，重写了 `description` 的 **Action-Object-Scope** 语义。将 `extract/sync/audit` 设为核心唤醒词。
- **“操作蓝图”制衡机制 (Iter-305)**: 针对 AI “走捷径”绕过工具手写正则的问题，引入了 `Blueprint` 强制步骤。模型必须先进行“风险评估”并列出“选定工具”才能执行。
- **动态环境感知 (Iter-300)**: 彻底重写了 `check_project_status`。引入 `os.listdir` 探测 `locales` 文件夹，实现了对 10+ 种语言项目的零配置自动适配，删除了干扰性的本地 `.i18n-skill.json`。
- **自更新闭环 (Iter-295)**: 增加了 `/i18n-update` 指令。AI 现已具备从 `skill.json` 自动解析仓库地址并执行 `gemini skills install --consent` 的能力。
- **UX 纠偏 (Iter-290)**: 针对输出乱码问题，在 `SKILL.md` 中强制加入了 UTF-8 编码一致性约束。

## 📍 [Phase 3] 鲁棒性加固与隐私治理 (Turns 151 - 250)
**核心突破：从“能跑”进化到“可信”，建立了主权级防御体系。**

- **隐私护盾研发 (Iter-240)**: 经历了十余次正则调试，最终确立了 `SENSITIVE_PATTERNS`。实现了对 API Key、Email、IP 和 Phone 的启发式掩码（Masking）。
- **快照回归系统 (Iter-220)**: 开发了 `snapshot.py`。引入了基于哈希的质量防线，解决了 AI 翻译质量随会话长度增加而下降的“退化”问题。
- **VCS 深度集成 (Iter-200)**: 多轮调试 `git apply` 和 `git hunk` 逻辑。实现了只扫描改动行号的“手术刀级”提取，极大节省了 Token 消耗。
- **类型系统收敛 (Iter-180)**: 经历了长达 30 轮的 Mypy 纠错。消除了 `tools.py` 中所有的 `Any` 泄露，补齐了 Pydantic 模型的 `Optional` 声明。
- **跨平台适配 (Iter-160)**: 修复了 Windows 盘符大小写导致的 `PermissionError` 路径穿越校验失败问题。

## 📍 [Phase 2] 逻辑引擎与 SOP 确立 (Turns 51 - 150)
**核心突破：模块化、结构化、协议化。**

- **双阶段提交协议 (Iter-140)**: 确立了 `Proposal (JSON ID) -> Review (Refine) -> Commit` 的闭环流程。解决了 AI 擅自修改源码的不可控问题。
- **AST 级提取引擎 (Iter-120)**: 从简单的字符串搜索转向基于语境的提取。支持了嵌套 Key 自动拍平（Flatten）与递归还原算法。
- **自纠错反馈循环 (Iter-100)**: 当占位符不一致时，工具会返回 `ValidationFeedback` 结构，引导 AI 自动重试翻译任务。
- **Pangu Linter 整合 (Iter-80)**: 引入了中英混排自动加空格（盘古之白）和标点符号自动纠正逻辑。

## 📍 [Phase 1] 原始积累与 Bootstrapping (Turns 1 - 50)
**核心突破：从 0 到 1 的混沌初开。**

- **项目骨架搭建 (Iter-40)**: 确立了 `pyproject.toml` 和 `i18n_agent_skill/` 包结构。
- **初步正则探索 (Iter-20)**: 调试对 React 模板字符串和 Vue 模板指令的提取正则。
- **沙箱校验起步 (Iter-10)**: 建立了第一个 `_validate_safe_path` 拦截器。

---
*This trace is a living document of AI self-correction and human-led engineering excellence.*
