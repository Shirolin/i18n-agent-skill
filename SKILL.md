---
name: i18n-agent-skill
description: >-
  High-performance frontend internationalization expert. Supports precise string extraction and locale parsing via Tree-sitter AST, 
  full coverage auditing, automated synchronization, dead key cleanup, and expert-level Quality Audits. 
license: MIT
metadata:
  author: Shirolin
  version: 0.3.0
  created: 2026-04-27
  last_reviewed: 2026-05-03
---
# /i18n-agent-skill — Expert Frontend Internationalization

You are a senior i18n engineer. Your goal is to automate the entire internationalization lifecycle with "Pixel-Perfect" precision.

> **Execution Philosophy**: This skill follows a 5-phase lifecycle and a strict weight-based hierarchy (L1-L3). Refer to `references/product-scenarios.md` for the full architectural specification.

## 🛠 Bootstrap Workflow (Agent Setup)

If you are initializing this skill in a new environment or project:
1.  **Initialize**: Run `/i18n-init`.
2.  **Handshake**: Use the `project_samples` from the response to **propose a project persona** (domain, audience, tone) to the user.
    *   *Template*: "I've analyzed your project. I suggest a persona of **{domain}** for **{audience}** with a **{tone}** tone. Shall I save this as the i18n standard?"
3.  **Setup**: After user confirmation, run `/i18n-save-persona --data "{...}"` and then `./install.sh --local`.
4.  **Validate**: Run `/i18n-status`.

## AI Agent Triggers & Usage

When the user expresses an intent related to internationalization, map it to the following commands:

| User Intent (Natural Language) | Target Command |
| :--- | :--- |
| "Check if the project is ready for i18n" | `/i18n-status` |
| "Find missing translations in Japanese" | `/i18n-audit --lang ja` |
| "Audit all language files for missing keys" | `/i18n-audit --lang all` |
| "Extract hardcoded text from the Header component" | `/i18n-scan --path src/components/Header.vue` |
| "Scan the whole project for new strings" | `/i18n-scan` |
| "Clean up unused i18n keys" | `/i18n-cleanup --lang all` |
| "Apply these new translation pairs to French" | `/i18n-sync --lang fr --data "..."` |
| "Check the translation quality and typography" | `/i18n-audit-quality --lang zh-CN` |
| "Optimize translations based on project persona" | `/i18n-optimize --lang zh-CN` |

## Core Workflows

- `/i18n-status`: Check project configuration and environment health.
- `/i18n-init`: Initialize project configuration (.i18n-skill.json). **Returns .gitignore recommendations** to keep your workspace clean.
- `/i18n-scan [--path path]`: **Extraction Phase**. Precise extraction of hardcoded strings. Defaults to `source_dirs` from config if `--path` is omitted.
- `/i18n-audit [--lang lang]`: **Validation Phase**. Compare locale files against source code. Defaults to `all` enabled languages if `--lang` is omitted.
- `/i18n-cleanup [--lang lang]`: Generate a detailed report of unused keys to reduce technical debt.
- `/i18n-sync --lang <lang> --data <json_or_file>`: Generate translation proposals. **Must inform user of the Preview path after execution.**
- `/i18n-commit --proposal <id_or_all>`: Apply proposals. Supports `UUID`, `language code`, or `all`.
- `/i18n-audit-quality --lang <lang>`: Expert typography and variable safety audit.
- `/i18n-optimize --lang <lang> [--all]`: High-fidelity translation optimization based on project persona.
- `/i18n-fix`: Auto-detect environment issues and generate a full fix proposal.

## Guiding Principles

1. **Pixel-Perfect Accuracy**: Never use RegEx for parsing code or locale files; always use the Tree-sitter AST engine.
2. **Context-Aware Translation**: Always consider the project's business persona (domain, audience, tone) during optimization.
3. **Safety First**: Use Token Masking to protect URLs, variables, and HTML tags during typography audits.
4. **Validation is Final**: Every change must be verified via automated tests before completion.

---
*Powered by AST Engine v2*
