---
name: i18n-agent-skill
description: 专门用于前端 i18n 工程化任务。核心优势：基于 Tree-sitter AST 的语法级提取、100% 物理隔离注释、支持嵌套模板字符串及 JSX/Vue 文本节点。
---

# i18n-agent-skill 执行协议 (Orchestration Specification)

## 🛠️ 环境预要求 (Prerequisites)
- **运行环境**: 必须在 Python 3.10, 3.11 或 3.12 环境下运行。
- **核心依赖**: 必须在技能根目录执行 `pip install -e .` 以激活 Tree-sitter AST 引擎。
- **状态验证**: 运行 `python -m i18n_agent_skill status` 确认环境已 Ready。

## 🎯 任务蓝图 (The Blueprint)
在处理任何国际化任务前，你必须向用户展示包含以下要素的操作蓝图：
1. **核心意图**: 描述提取或同步的目标。
2. **提取策略**: 告知将利用 Tree-sitter 执行语法级解析。
3. **安全审计**: 告知隐私盾开启状态。
4. **质量评审**: 声明将执行占位符一致性与风格校验。

---

## ⚡ 任务流编排 (Workflows)

### 1. 全量/增量国际化审计
**执行路径**:
1. **状态探测**: 执行 `python -m i18n_agent_skill status`。
2. **全语言体检**: 执行 `python -m i18n_agent_skill audit all`。
3. **精准提取**: 对目标文件执行 `scan` 指令。

### 2. 自动化重构与同步
**执行路径**:
1. **翻译自审**: 检查结果是否符合 `GLOSSARY.json` 并确保占位符未丢失。
2. **生成提案**: 调用 `sync` 子命令生成提案。
3. **应用变更**: 经用户批准后，调用 `commit` 应用变更。

---

## 🔒 指令约束 (Guardrails)
1. **禁止正则**: 严禁手写正则扫描源码。必须强制使用 AST 引擎。
2. **隐私优先**: 严禁在 `telemetry` 报告显示有隐私风险时忽略脱敏逻辑。
3. **物理隔离**: 无需手动编写注释拦截代码，引擎已天然免疫注释干扰。

---

## 💡 快捷指令
- `/i18n-audit`: 执行全量 AST 差异审计。
- `/i18n-fix`: 执行审计、环境自愈并生成修复提案。
- `/i18n-update`: 运行 `gemini skills install ...` 更新引擎。
