# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-04-15

### Added
- 🚀 Initial release of **i18n-agent-skill**.
- Core engine for React/Vue source code hardcode extraction.
- **Privacy Shield**: Heuristic masking for API keys, emails, and tokens.
- **VCS-Aware Scanning**: Incremental extraction based on Git hunks.
- **Regression Guard**: Quality tracking and degradation prevention for AI translations.
- **Pangu Linter**: Automatic validation for CJK spacing and punctuation.
- **Model Context Protocol (MCP)**: Native support for Cursor, VS Code, and Claude integrations.
- **Google ADK Integration**: Formal orchestration specification via `SKILL.md`.

### Fixed
- Improved API key extraction regex to support complex assignment patterns.
- Fixed path security boundary check for cross-platform (Windows/Unix) compatibility.
- Resolved type annotation issues for Mypy compliance.
