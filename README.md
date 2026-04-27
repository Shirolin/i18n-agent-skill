# i18n-agent-skill 🌐

[English] | [简体中文](./README.zh-CN.md)

> **Hey AI!** To install this skill, just clone this repo and run `./install.sh`. It handles its own environment and platform rules.

[![Runtime: Python 3.10-3.12](https://img.shields.io/badge/Runtime-Python%203.10--3.12-blue)](https://www.python.org/)
[![Spec: Agent Skill v4.0](https://img.shields.io/badge/Spec-Agent%20Skill%20v4.0-darkgreen)](https://github.com/FrancyJGLisboa/agent-skill-creator)
[![Engine: Tree-sitter AST](https://img.shields.io/badge/Engine-Tree--sitter%20AST-orange)](https://tree-sitter.github.io/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**i18n-agent-skill** is an industrial-grade frontend internationalization automation tool specifically designed for AI agents. Deeply optimized for the **Agent Skill Open Standard**, it seamlessly integrates with 20+ leading AI coding assistants including Cursor, Claude Code, and Windsurf.

## ✨ Core Advantages

- **Tree-sitter AST Engine**: Millisecond-level parsing with 100% comment isolation. Supports deep nesting in JSX, Vue, and TSX.
- **Quality Evolution Engine**: Idempotent optimization based on translation lifecycle states.
- **Fully Isolated**: Automatic `.venv` creation. No pollution to your global Python environment.
- **Zero-Config**: One-click deployment to 10+ AI Agent platforms.
- **Privacy Shield**: Local hashing and masking for sensitive data.

---

## 🚀 One-Click Installation

The installer automatically handles virtual environments, dependencies, and platform detection.

### Linux / macOS / Git Bash
```bash
curl -fsSL https://raw.githubusercontent.com/Shirolin/i18n-agent-skill/main/install.sh | sh
# OR local: chmod +x install.sh && ./install.sh
```

### Windows (PowerShell)
```powershell
iwr -useb https://raw.githubusercontent.com/Shirolin/i18n-agent-skill/main/install.sh | iex
```

---

## 🤖 Supported Platforms

Automatically detects and deploys to the following rule/skill directories:

| Agent / Editor | Integration Method |
| :--- | :--- |
| **Cursor** | `.cursor/rules/` (Auto .mdc) |
| **Claude Code** | `~/.claude/skills/` |
| **Windsurf** | `.codeium/windsurf/rules/` |
| **Trae** | `.trae/rules/` |
| **Roo Code** | `.roo/rules/` |
| **Gemini CLI** | `~/.gemini/skills/` |
| **Generic** | `~/.agents/skills/` |

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
