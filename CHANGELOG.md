# AI Evolution & Modification Trace 📜

本项目记录了 AI 助手在人类指引下，经历数百轮对话、数千次逻辑修正所达成的工程化成果。

## 📍 [Phase 6] AST 结构化革命 (Turns 351 - 400+)
**当前阶段：彻底终结正则补丁时代，建立基于 Tree-sitter 的工业级提取内核。**

- **Tree-sitter 架构集成 (Iter-395)**: 放弃所有脆弱的正则匹配和字符级状态机。通过引入 `tree-sitter-javascript`, `tree-sitter-tsx`, `tree-sitter-vue` 实现了对源码的像素级解析。
- **声明式查询 (S-Expressions) (Iter-390)**: 引入 Tree-sitter Query 语法。
    - **JSXText 捕获**: 物理级解决“无引号文本”盲区，100% 覆盖 React/Vue 文本节点。
    - **属性语义锚定**: 仅针对 `placeholder/title/label` 等 UI 属性进行提取，物理屏蔽 `className/id` 等工程干扰。
- **模板嵌套解析**: AST 原生支持模板字符串解构，彻底解决了`${}` 嵌套导致的提取破碎与代码破坏风险。
- **依赖自愈提示**: 在 `ErrorInfo` 中补全了针对 Tree-sitter 库缺失的自愈指令。

## 📍 [Phase 5] 架构降维与 CLI 优先 (Turns 321 - 350)
- **CLI-First 双模驱动**: 彻底重写了 `__main__.py`，支持 `audit all` 全量体检。
- **自愈式帮助系统**: 补全了所有子命令的 `--help` 逻辑。

## 📍 [Phase 4] 协议主权与架构博弈 (Turns 251 - 320)
- **SKILL.md 准入大修**: 修复 YAML Frontmatter 缺失问题。
- **操作蓝图机制**: 引入 `Blueprint` 强制步骤，规避 AI 的“捷径思维”。

---
*Generated with ❤️ by Gemini CLI - From Regex Hack to AST Mastery.*
