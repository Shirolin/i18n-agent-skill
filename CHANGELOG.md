# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-04-15

### Added
- 🚀 Initial release of **i18n-agent-skill**.
- **Engineering Overhaul**: Rebuilt the testing suite using `pytest`, introducing 19 core/integration test cases covering privacy, quality, and I/O.
- **AI-First Orchestration**: Re-architected `SKILL.md` based on Google ADK paradigms to support "One-Sentence Delivery" (Impeccable Mode).
- **Modern CI/CD**: Established a rigorous quality gate with Ruff and Mangu-standard Mypy type checks.
- **Privacy Shield**: Heuristic masking for API keys, emails, and tokens.
- **VCS-Aware Scanning**: Incremental extraction based on Git hunks.
- **Pangu Linter**: Automatic validation for CJK spacing and punctuation.
- **Model Context Protocol (MCP)**: Native support for Cursor, VS Code, and Claude integrations.

### Fixed
- **Core Stability**: Resolved critical bugs in `_detect_locale_dir` and `refine_i18n_proposal` functions.
- **Security Boundary**: Hardened path validation logic for Windows/Unix cross-platform compatibility.
- **Regex Optimization**: Enhanced extraction patterns to capture complex string templates and sensitive tokens.
- **CI Environment**: Upgraded runtime to Python 3.10 and Node.js 24 runner to meet modern dependency requirements.
- **SDK Exports**: Refined `__init__.py` to provide a clean, top-level Python API.
