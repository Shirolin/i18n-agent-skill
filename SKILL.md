---
name: i18n-agent-skill
description: 专门用于前端 i18n 工程化任务。核心优势：具备 AST 级源码提取、自动化隐私脱敏（Privacy Shield）、多语言 Key 差异精算以及翻译质量回归保护。
---

# i18n-agent-skill 执行协议 (Orchestration Specification)

## 🛠️ 环境预要求 (Prerequisites)
- **环境**: 需要 Python 3.10+。
- **依赖**: 首次安装后，必须在技能根目录执行 `pip install -e .`。
- **配置**: `.i18n-skill.json` 可选，若缺失则启用启发式探测。

## 🎯 工具能级矩阵 (Tool Capabilities Matrix)
在决策任务路径时，请参考下表：

| 任务类型 | 通用方法 (原生工具) | 本技能专用工具 (MCP) | 结论 |
| :--- | :--- | :--- | :--- |
| **文案扫描** | `grep_search` (简单正则) | `scan_file` (AST 探测 + **隐私脱敏**) | **必须使用 MCP**: 通用搜索无法处理敏感信息风险。 |
| **差异比对** | `read_file` (人工比对) | `get_missing_keys` (集合算法) | **必须使用 MCP**: 大文件人工比对极易漏项且浪费 Token。 |
| **同步写入** | 手写文件覆盖 | `propose_sync` (**回归保护 + 占位符校验**) | **必须使用 MCP**: 手写无法检测占位符不一致导致的线上 Bug。 |

---

## ⚡ 任务流编排 (Workflows)

处理任何请求前，你必须先生成 **操作蓝图 (Blueprint)**：
1. **意图**: [如：审计 zh-CN 缺失]
2. **风险评估**: [如：文件超过 500 行，手动比对存在高失误率]
3. **选定工具**: [必须从 MCP 工具集中选择]

### 1. 国际化审计与同步 SOP
**适用场景**: 检查翻译缺失、同步变动。
**步骤**:
1.  **探测**: 调用 `check_project_status` 获取当前隐私等级和 VCS 状态。
2.  **精算差异**: 调用 `get_missing_keys` 获取底层算出的差异集。**严禁手动读取文件比对**。
3.  **增量扫描**: 调用 `scan_file` 配合 `vcs_mode=True` 获取 Git 变动中的残留硬编码。
4.  **安全同步**: 调用 `propose_sync` 生成带 `proposal_id` 的提案。

### 2. 全量重构重塑 SOP
**适用场景**: 遗留代码 i18n 化。
**步骤**:
1.  **脱敏提取**: 调用 `scan_file` 必须开启隐私盾。
2.  **语义 Key 生成**: 基于工具返回的上下文生成 Key。
3.  **原子提交**: 必须通过 `commit_i18n_changes` 确保快照更新。

---

## 🔒 指令约束 (Guardrails)
1.  **隐私第一**: 所有外传到翻译接口的文案，必须经过 `scan_file` 的脱敏过滤。
2.  **质量回路**: 必须通过 `propose_sync` 的 `regression_alert` 反馈来优化翻译结果。
3.  **编码一致性**: 所有文件读写均强制使用 UTF-8，杜绝乱码。

## 💡 快捷指令
- `/i18n-audit`: 调用 `get_missing_keys` + `scan_file`。
- `/i18n-fix`: 执行审计并自动生成修复提案。
