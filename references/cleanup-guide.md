# Dead Key Detection & Cleanup Guide

## Overview

In long-running frontend projects, locale files often accumulate "dead keys"—translation entries that are no longer referenced in the source code. This technical debt increases bundle size and translation costs.

**i18n-agent-skill** provides an AST-based cleanup engine to safely identify these keys.

## How it Works

The cleanup process involves three high-precision stages:

### 1. Locale Key Flattening
The tool loads the target locale file (e.g., `en.json` or `en.ts`) and flattens it into a set of dot-notated paths:
`{ "auth": { "login": "..." } }` -> `auth.login`

### 2. AST-Based Usage Scanning
Instead of error-prone grep/regex, the tool uses **Tree-sitter** to scan source files (`.js`, `.jsx`, `.ts`, `.tsx`, `.vue`). It specifically looks for i18n function calls:
- `t('key')`
- `$t('key')`
- `i18n.t('key')`
- `useTranslation` hooks

### 3. Set Difference Calculation
Dead Keys = `(All Locale Keys) - (All Used Keys Found in Source)`

## Limitations & Best Practices

- **Dynamic Keys**: If your project constructs keys dynamically (e.g., `t(`status.${code}`)`), the AST scanner may mark them as unused because it cannot infer the runtime value of `${code}`.
- **Recommendations**:
    - Before mass-deleting keys, run `/i18n-cleanup` to review the report.
    - If you use dynamic keys, consider adding them to the `ignored_keys` list in `.i18n-skill.json`.

## Commands

```bash
# General report
/i18n-cleanup --lang en

# Part of general audit
/i18n-audit en
```
