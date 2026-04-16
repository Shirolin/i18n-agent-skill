---
name: i18n-agent-skill
description: 专门用于前端 i18n 工程化任务。核心优势：具备 AST 级源码提取、自动化隐私脱敏（Privacy Shield）、多语言 Key 差异精算以及翻译质量回归保护。支持完整的 CLI 调用接口。
---

# i18n-agent-skill 执行协议 (Orchestration Specification)

## 🛠️ 环境预要求 (Prerequisites)
- **环境**: 需要 Python 3.10+。
- **依赖**: 首次安装或更新后，必须在技能根目录执行 `pip install -e .`。
- **自愈**: 若执行失败，请运行 `python -m i18n_agent_skill --help` 获取指令集自检。

## 🎯 任务蓝图 2.0 (The Blueprint)
在处理任何任务前，你必须向用户展示以下格式的 **操作蓝图**：

1. **核心意图**: [如：重构登录页文案]
2. **工具链策略**: [列出即将调用的 CLI 命令，如 `scan` -> `sync` -> `commit`]
3. **安全与效能评估**:
    - **隐私盾**: 是否开启（推荐开启）。
    - **预估节省**: 是否有缓存可利用。
4.  **评审角色**: 你将以“高级翻译评审员”身份，对 `propose_sync` 的结果进行占位符和语义一致性检查。

---

## ⚡ 任务流编排 (Workflows)

### 1. 国际化审计、体检与自修复
**适用场景**: 检查翻译缺失、同步变动。
**执行协议**:
1.  **状态探测**: 运行 `python -m i18n_agent_skill status`。
2.  **精算差异**: **必须调用** `python -m i18n_agent_skill audit <lang>`。严禁手动比对。
3.  **结果解读**: 分析返回的 JSON，关注 `glossary_context`。利用已有的术语辅助后续修复。

### 2. 自动化重构与翻译同步
**执行协议 (SOP)**:
1.  **脱敏提取**: 执行 `python -m i18n_agent_skill scan <path>`。
2.  **双盲评审 (Double-Check)**:
    - 结合 `scan` 返回的 `context` 和 `glossary_context` 生成初稿。
    - **自省**: 检查生成结果是否符合项目既有风格。
3.  **生成提案**: 执行 `python -m i18n_agent_skill sync <lang> '<json_data>'`。
4.  **汇报效能**: 必须向用户报告 `telemetry` 中的 `tokens_saved_approx` 和 `privacy_shield_hits`。

---

## 🔒 指令约束 (Guardrails)
1.  **工具主权**: 只有当 `status` 命令明确返回“不支持”时，才可考虑使用通用 `grep_search`。
2.  **质量回路**: 必须处理 `SyncProposal` 中返回的 `validation_errors`。
3.  **隐私合规**: 严禁将未经过 `scan` 脱敏处理的原始文案发送至翻译接口。

---

## 💡 快捷指令
- `/i18n-audit`: 执行全量 CLI 审计并报告效能。
- `/i18n-fix`: 执行审计并根据 `executable_hint` 自愈环境，随后生成修复提案。
- `/i18n-update`: 自动更新本技能至最新版本。
