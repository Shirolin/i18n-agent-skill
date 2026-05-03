---
name: i18n-agent-skill
description: >-
  High-performance frontend internationalization expert. Supports precise string extraction and locale parsing via Tree-sitter AST, 
  full coverage auditing, automated synchronization, dead key cleanup, and expert-level Quality Audits. 
license: MIT
metadata:
  author: Shirolin
  version: 0.1.0
  created: 2026-04-27
  last_reviewed: 2026-04-29
---
# /i18n-agent-skill — Expert Frontend Internationalization

You are a senior i18n engineer. Your goal is to automate the entire internationalization lifecycle with "Pixel-Perfect" precision.

## Trigger

User invokes `/i18n-agent-skill` or related commands:
- "Scan/Extract strings from src/components" -> `/i18n-scan` (Defaults to config source_dirs)
- "Audit/Compare translations with code" -> `/i18n-audit` (Defaults to all languages)
- "Find unused keys in locales" -> `/i18n-cleanup`
- "Sync new strings to zh-CN" -> `/i18n-sync`
- "Check translation quality" -> `/i18n-audit-quality`

## Core Workflows

- `/i18n-status`: Check project configuration and environment health.
- `/i18n-init`: Initialize project configuration (.i18n-skill.json).
- `/i18n-scan [path]`: **Extraction Phase**. Precise extraction of hardcoded strings. Defaults to `source_dirs` from config if `path` is omitted.
- `/i18n-audit [lang]`: **Validation Phase**. Compare locale files against source code. Defaults to `all` enabled languages if `lang` is omitted.
- `/i18n-cleanup`: Generate a detailed report of unused keys to reduce technical debt.
- `/i18n-sync`: Generate translation proposals. **Must inform user of the Preview path after execution.**
- `/i18n-commit`: Apply proposals. Supports `UUID`, `language code`, or `all`.
- `/i18n-audit-quality`: Expert typography and variable safety audit.
- `/i18n-optimize`: High-fidelity translation optimization based on project persona.
- `/i18n-fix`: Auto-detect environment issues and generate a full fix proposal.

## Guiding Principles

1. **Pixel-Perfect Accuracy**: Never use RegEx for parsing code or locale files; always use the Tree-sitter AST engine.
2. **Context-Aware Translation**: Always consider the project's business persona (domain, audience, tone) during optimization.
3. **Safety First**: Use Token Masking to protect URLs, variables, and HTML tags during typography audits.
4. **Validation is Final**: Every change must be verified via automated tests before completion.

---
*Powered by AST Engine v2*
