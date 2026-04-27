# i18n-agent-skill 🌐

[English] | [简体中文](./README.zh-CN.md)

[![Runtime: Python 3.10-3.12](https://img.shields.io/badge/Runtime-Python%203.10--3.12-blue)](https://www.python.org/)
[![Spec: Agent Skill v4.0](https://img.shields.io/badge/Spec-Agent%20Skill%20v4.0-darkgreen)](https://github.com/FrancyJGLisboa/agent-skill-creator)
[![Engine: Tree-sitter AST](https://img.shields.io/badge/Engine-Tree--sitter%20AST-orange)](https://tree-sitter.github.io/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**i18n-agent-skill** is an industrial-grade frontend internationalization automation tool specifically designed for AI agents. Deeply optimized for the **Agent Skill Open Standard**, it seamlessly integrates with 20+ leading AI coding assistants including Cursor, Claude Code, and Windsurf.

## ✨ Core Advantages

- **Tree-sitter AST Engine**: Millisecond-level parsing with 100% comment isolation. Supports deep nesting in JSX, Vue, and TSX.
- **Quality Evolution Engine**: Idempotent optimization based on translation lifecycle states (Draft/Reviewed/Approved). Automatically learns terminology from human corrections.
- **Expert Quality Audit**: Generates in-depth reports identifying terminology inconsistencies, missing context, and non-native phrasing.
- **Cross-Language Semantic Projection**: Anchors translations to your familiar language (e.g., zh-CN) to ensure semantic consistency across all target languages.
- **Privacy Shield**: Local hashing and masking for API Keys and PII, ensuring sensitive data never leaves your sandbox.
- **Global Native**: Fully compliant with Google ADK paradigms, supporting multi-language `SKILL.md` and decoupled English-first code logic.
- **Cross-Platform**: Standard `SKILL.md` format for one-click installation into any modern AI assistant environment.
- **Automated Typography**: Built-in multi-language Linter for CJK spacing and punctuation consistency.

---

## 🚀 Quick Start

### 1. One-click Installation (5 seconds)

Run the installer in your project root:

```bash
# Auto-detects environment, installs dependencies, and deploys to AI assistants
chmod +x scripts/install-skill.sh
./scripts/install-skill.sh
```

### 2. Activate in AI Assistant

Once installed, type the following in any supported AI assistant:

> **"/i18n-agent-skill scan hardcoded strings in src directory"**

---

## 📖 Core Command Set

| Command | Description |
| :--- | :--- |
| `/i18n-audit` | Coverage Audit: Check for missing keys across locale files. |
| `/i18n-audit-quality` | **Quality Audit**: Generate expert reports on phrasing and consistency. |
| `/i18n-pivot-sync` | **Semantic Projection**: Sync target languages based on a familiar reference language. |
| `/i18n-fix` | Quick Fix: Auto-detect environment issues and generate recovery proposals. |
| `/i18n-status` | Status Check: Verify project configuration and readiness. |
| `/i18n-sync` | Smart Sync: Perform incremental translation synchronization. |

---

## 📂 Project Structure

```text
i18n-agent-skill/
├── i18n_agent_skill/   # Core Python logic package
├── scripts/            # Automation scripts: install.sh, CLI tools
├── references/         # Technical docs: AST, Privacy, Linter rules
├── assets/             # Configuration assets: glossary templates, etc.
├── tests/              # Automated test suite (Unit & Integration)
├── SKILL.md            # Primary execution protocol (v4.0 Spec)
└── pyproject.toml      # Dependency management and project index
```

---

## 🛠 Development & Validation

This project integrates standard validation tools:

```bash
# Verify protocol compliance
python .agents/skills/agent-skill-creator/scripts/validate.py .

# Run security scan
python .agents/skills/agent-skill-creator/scripts/security_scan.py .

# Run tests
pytest
```

---

## 🔒 Security Policy

We guarantee that your source code is never uploaded to third-party servers. All parsing, de-identification, and suggestion generation occur locally. The AI only receives masked snippets to assist with translation under your explicit permission.

---

## 📄 License

[Apache-2.0](LICENSE)
