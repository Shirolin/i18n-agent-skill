---
name: i18n-agent-skill
description: 专门用于前端 i18n 工程化任务。功能涵盖：从源码提取(extract)硬编码中文、重构(refactor)为 i18n 变量、同步(sync)多语言翻译包、审计(audit)翻译质量及执行隐私脱敏(privacy)。
---

# i18n-agent-skill 执行协议 (Orchestration Specification)

## 🛠️ 环境预要求 (Prerequisites)
- **环境**: 需要 Python 3.10+。
- **依赖**: 首次安装后，请确保在技能根目录执行 `pip install -e .` 以激活 MCP 驱动。
- **配置**: `.i18n-skill.json` 为可选配置。若存在，技能将遵循该文件的路径及规则；若缺失，技能将尝试自动探测项目结构。

## 🎯 激活场景 (Trigger Scenarios)
... (保持原有内容) ...

---

## ⚡ 任务流编排 (Workflows)

当你接收到指令意图时，首先执行 **环境与上下文校验**：

### 0. 启发式上下文探测 (Context Discovery)
**操作步骤**:
1.  **探测配置**: 查找是否存在 `.i18n-skill.json`。
2.  **自动推断 (Heuristics)**: 若无配置文件，扫描当前工作区是否存在 `package.json`、`src/`、`locales/` 或 `i18n/` 文件夹。
3.  **零配置启动**: 
    - 若探测到明显的国际化迹象（如存在 `locales/*.json`），直接调用 `get_status` 获取当前状态。
    - 若探测结果模糊，主动询问用户：“未检测到 i18n 配置文件，是否以默认配置（扫描 src、同步至 locales 目录）开始任务？”
4.  **MCP 连通性**: 尝试调用 `get_status`，若失败则指导用户检查 Python 依赖。

### 1. 全量国际化改造 (`/i18n-refactor`)
... (后续逻辑) ...
**适用场景**: 将硬编码项目改造为 i18n 项目。
**执行协议 (SOP)**:
1.  **探测**: 调用 `get_status` 确认 `enabled_langs` 和目录结构。
2.  **提取**: 调用 `scan_file` 对全量源码执行提取。
3.  **翻译**: 基于提取出的 `ExtractedString` 及其上下文，执行翻译并生成语义化 Key。
4.  **同步**: 循环调用 `propose_sync` 提交各语言提案。
5.  **重构**: 在用户确认后，调用 `commit_changes` 并分步骤执行源码替换。

### 2. 项目审计与同步 (`/i18n-audit`)
**适用场景**: 检查翻译缺失并同步 Git 变动。
**执行协议 (SOP)**:
1.  **扫描**: 调用 `scan_file` (开启 `vcs_mode`) 提取 Git 变动。
2.  **比对**: 调用 `get_missing_keys` 找出缺失翻译。
3.  **修复**: 生成缺失翻译并调用 `propose_sync`。同步执行风格校验。
4.  **核对**: 若返回 `regression_alert`，需分析原因并优化翻译结果。

---

## 🔒 指令约束 (Guardrails)

1.  **数据脱敏**:
    - 禁止尝试还原被掩码（`[MASKED_XXX]`）的信息。
    - 文案外传前必须执行 `scan_file` 进行本地脱敏。
2.  **质量要求**:
    - 必须处理 `propose_sync` 返回的质量退化告警。
    - 确保翻译中的占位符与源文案保持一致。

---

## 💡 快捷指令
- `/i18n-fix`: 执行审计与修复。
- `/i18n-sync`: 执行增量同步。
- `/i18n-terms`: 术语库维护。

