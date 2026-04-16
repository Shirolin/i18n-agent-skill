---
name: i18n-agent-skill
description: 专门用于前端 i18n 工程化任务。核心优势：具备 AST 级源码提取、自动化隐私脱敏、翻译缺失审计及质量回归保护。支持完整的 CLI 调用接口。
---

# i18n-agent-skill 执行协议 (Orchestration Specification)

## 🛠️ 环境预要求 (Prerequisites)
- **环境**: 需要 Python 3.10+。
- **依赖**: 首次安装后，必须在技能根目录执行 `pip install -e .`。
- **验证**: 运行 `python -m i18n_agent_skill --help` 确认 CLI 可用。

## 🎯 任务蓝图 (Blueprint) 与工具选择
当用户提出 i18n 相关需求时，你必须使用 **CLI 优先策略**。通过 `run_shell_command` 调用具体的子命令。

| 任务类型 | 推荐 CLI 指令 | 预期输出 |
| :--- | :--- | :--- |
| **项目预检** | `python -m i18n_agent_skill status` | 项目配置、已启用语言、Git 变更摘要。 |
| **文案扫描** | `python -m i18n_agent_skill scan <path> [--vcs]` | 包含行号、上下文及隐私屏蔽标识的 JSON 列表。 |
| **差异审计** | `python -m i18n_agent_skill audit <target_lang>` | 基准语言与目标语言的 Key 差异集合。 |
| **生成提案** | `python -m i18n_agent_skill sync <lang> <json_data>` | 包含 `proposal_id` 和质量评估的同步提案。 |
| **应用变更** | `python -m i18n_agent_skill commit <proposal_id>` | 变更正式落盘并更新回归快照。 |

---

## ⚡ 任务流编排 (Workflows)

### 1. 自动化翻译体检与审计
**意图**: “检查翻译缺失”、“翻译体检”。
**SOP**:
1. **获取状态**: 执行 `python -m i18n_agent_skill status` 确认当前项目语言。
2. **执行审计**: 对每一门启用语言，执行 `python -m i18n_agent_skill audit <lang>`。
3. **扫描源码**: 执行 `python -m i18n_agent_skill scan src --vcs` 查找未提取的硬编码。
4. **生成报告**: 汇总以上 JSON 结果提供给用户。

### 2. 自动化国际化重构
**意图**: “提取中文”、“重构代码”。
**SOP**:
1. **精准扫描**: 执行 `python -m i18n_agent_skill scan <file_path>` 获取提取结果。
2. **翻译并同步**: 
    - 结合提取结果生成翻译。
    - 执行 `python -m i18n_agent_skill sync <lang> '<json_data>'` 生成提案。
3. **应用重构**: 得到用户确认后，执行 `python -m i18n_agent_skill commit <proposal_id>`。

---

## 🔒 指令约束 (Guardrails)
1. **严禁手写逻辑**: **禁止**使用手写正则或 `read_file` 自行比对 JSON。必须调用上述 CLI 命令并解析返回的 JSON。
2. **自愈能力**: 如果命令返回错误或超时，请尝试运行 `python -m i18n_agent_skill --help` 查看最新参数说明。
3. **隐私合规**: 必须确保 `scan` 命令的隐私屏蔽逻辑正常工作，严禁将未脱敏的 API Key 发送至翻译接口。

---

## 💡 快捷指令
- `/i18n-audit`: 执行全量 CLI 审计。
- `/i18n-update`: 运行 `gemini skills install https://github.com/Shirolin/i18n-agent-skill --consent --scope workspace`。
