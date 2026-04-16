---
name: i18n-agent-skill
description: 专门用于前端 i18n 工程化任务。核心优势：基于 Tree-sitter AST 的语法级提取、100% 免疫注释干扰、支持嵌套模板字符串及 JSX/Vue 文本节点。支持全功能 CLI 调用。
---

# i18n-agent-skill 执行协议 (Orchestration Specification)

## 🛠️ 环境预要求 (Prerequisites)
- **环境**: 需要 Python 3.10+。
- **依赖**: 首次安装或更新后，必须在技能根目录执行 `pip install -e .` 以加载 Tree-sitter 核心库。
- **验证**: 运行 `python -m i18n_agent_skill --help` 确认 CLI 可用。

## 🎯 任务蓝图 (The Blueprint)
本技能已升级至 **v1.2 AST 引擎**。在处理任务前，你必须向用户展示操作蓝图：

1. **结构化提取策略**: [利用 Tree-sitter 捕获 JSXText / StringLiteral]
2. **上下文语义背景**: [通过 AST 溯源父节点信息，确保翻译不偏离业务逻辑]
3. **安全与效能**: [汇报隐私盾开启状态及 Telemetry 预估]

---

## ⚡ 任务流编排 (Workflows)

### 1. 全量国际化审计
**执行协议**:
1.  **状态探测**: 运行 `python -m i18n_agent_skill status`。
2.  **精算差异**: 必须执行 `python -m i18n_agent_skill audit all`。
3.  **语法级扫描**: 运行 `python -m i18n_agent_skill scan <path>`。AST 引擎会自动过滤注释及 `className/id` 等逻辑属性。

### 2. 自动化重构与同步
**执行协议**:
1.  **像素级提取**: 调用 `scan` 命令获取包含行号和 AST 来源的文案。
2.  **语义仲裁**: 
    - 针对 `scan` 返回的列表，结合 `context` 判定是否为 UI 文案。
    - **严禁** 翻译 CSS 类名、URL 或代码路径。
3.  **生成提案**: 执行 `python -m i18n_agent_skill sync <lang> '<json_data>'`。

---

## 🔒 指令约束 (Guardrails)
1.  **AST 优先**: 严禁退化回手写正则扫描。只有当 AST 解析失败时，才可申请人工介入。
2.  **物理隔离**: 引擎已物理屏蔽代码注释，无需再手动编写过滤逻辑。
3.  **质量回路**: 必须处理 `SyncProposal` 中反馈的占位符不一致问题。

---

## 💡 快捷指令
- `/i18n-audit`: 执行全语言 AST 审计。
- `/i18n-fix`: 执行审计并生成自愈修复提案。
- `/i18n-update`: 运行 `gemini skills install ...` 获取最新 AST 引擎。
