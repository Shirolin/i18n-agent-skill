# i18n-agent-skill 🌐

[English] | [简体中文](./README.zh-CN.md)

> **Industrial-grade frontend internationalization (i18n) lifecycle automation for AI coding assistants.**

[![Version](https://img.shields.io/badge/version-0.3.0-blue)](CHANGELOG.md)
[![Spec: Agent Skill v4.0](https://img.shields.io/badge/Spec-Agent%20Skill%20v4.0-darkgreen)](https://github.com/FrancyJGLisboa/agent-skill-creator)
[![Engine: Tree-sitter AST](https://img.shields.io/badge/Engine-Tree--sitter%20AST-orange)](https://tree-sitter.github.io/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**i18n-agent-skill** solves the complexity of internationalization within AI-native development workflows. By leveraging deterministic AST parsing and context-aware state management, it provides a safe, predictable, and fully automated bridge between source code and global translation files.

---

## 🔄 Automated i18n Loop

The skill automates the full lifecycle, ensuring zero hardcoded string leakage and human-verified translation quality.

```mermaid
graph LR
    A[Scan: AST Extraction] --> B[Audit: Diff Analysis]
    B --> C[Sync: Contextual Proposals]
    C --> D[Commit: Physical Write]
    D --> E[Quality: Feedback Loop]
    E --> C
```

---

## 🚀 AI-Native Installation (Quick Start)

The recommended way to install is to let your **AI Assistant** handle the heavy lifting.

1. **Clone the repository** to your project.
2. **Tell your AI Assistant**:
   > "Install this skill locally and check project status."

The assistant will automatically execute `./install.sh --local` and run `/i18n-status` to prepare your environment.

---

## 🛡️ Technical Pillars

### 1. Deterministic AST Parsing
Unlike fragile RegEx-based extractors, our engine uses **Tree-sitter AST** to navigate code structure.
- **Structural Accuracy**: Correctness in complex JSX/TSX nesting and template literals.
- **Zero-Noise Isolation**: Automatically ignores comments and non-UI code blocks.
- **Multi-Format Parsing**: Robust support for JSON, YAML, and JS/TS object-literal locale files.

### 2. Privacy Shield (Secure by Design)
Built for enterprise security. Your source code and sensitive data stay in your local environment.
- **Local Masking**: Automatically identifies and masks PII (Emails, API Keys, IPs) before AI interaction.
- **Deterministic Hashing**: Tracks changes via local hashes without ever uploading content.

### 3. State-Based Quality Evolution
Manages the translation lifecycle to prevent regressions and improve phrasing over time.
- **State Machine**: Tracks every key from `DRAFT` to `REVIEWED` and `APPROVED`.
- **Glossary Learning**: Automatically learns preferred terminology from manual human corrections.
- **Typography Linter**: Built-in rules for CJK-Western spacing and professional punctuation.

---

## 🌍 Language Support Matrix

| Language Family | Extraction (AST) | Translation (AI) | Typography Linting | Status |
| :--- | :---: | :---: | :---: | :--- |
| **English / Western** | ✅ | ✅ | ✅ | **Production** |
| **CJK (ZH, JA, KO)** | ✅ | ✅ | ✅ | **Production** |
| **European (Latin)** | ✅ | ✅ | ✅ | **Stable** |
| **RTL (Arabic, Hebrew)**| ✅ | ✅ | ⚠️ (Bypass) | **Beta (Sync only)** |
| **Other (Hindi, Thai)** | ✅ | ✅ | ⚠️ (Bypass) | **Beta (Sync only)** |

> **Note**: Professional typography rules (e.g., CJK spacing) are currently optimized for language families marked as "✅".

---

## 📖 Core Command Set (AI & Human Reference)

| Command | Capability | Detailed Functional Description |
| :--- | :--- | :--- |
| `/i18n-init` | **Initialization** | Scans project structure and generates an explicit `.i18n-skill.json` configuration. |
| `/i18n-status` | **Health Check** | Verifies dependencies, environment isolation, and current VCS (Git) state. |
| `/i18n-scan` | **Extraction** | Precision scan of source code to find hardcoded strings. Use `--path` for specific components. |
| `/i18n-audit` | **Gap Analysis** | Compares locale files against source code to find missing keys or detect unused "dead keys". |
| `/i18n-sync` | **Smart Staging** | Generates translation proposals. Merges new keys into a staging area with Markdown preview. |
| `/i18n-commit` | **Apply Changes** | Formally writes approved proposals to physical locale files and updates quality snapshots. |
| `/i18n-cleanup` | **Debt Control** | Specifically identifies and reports unused i18n keys to keep locale files lean. |
| `/i18n-audit-quality` | **Expert Audit** | Generates a quality report focusing on phrasing, variable safety, and typography. |
| `/i18n-pivot-sync` | **Projection** | Optimizes target languages based on a familiar reference language (e.g., zh-CN). |
| `/i18n-fix` | **Auto-Repair** | Diagnoses environment or configuration issues and proposes recovery steps. |

---

## 🤖 Integration Blueprint

The installer automatically detects and deploys to your preferred Agent environment:

| Agent / Editor | Integration Method | Target Path |
| :--- | :--- | :--- |
| **Cursor** | Native Rules | `.cursor/rules/` (Auto-generated .mdc) |
| **Claude Code** | Global Skills | `~/.claude/skills/` |
| **Gemini CLI** | User Skills | `~/.gemini/skills/` |
| **Windsurf / Trae** | Global Rules | `.codeium/windsurf/rules/` / `.trae/rules/` |
| **Generic ADK** | Universal Path | `~/.agents/skills/` |

---

## 📂 Project Structure

```text
i18n-agent-skill/
├── i18n_agent_skill/   # Core Python logic package
├── scripts/            # Automation: installers, cleanup, and wrappers
├── references/         # Knowledge base: AST engine, Privacy Guard, Linting specs
├── assets/             # Templates: glossary, persona blueprints
├── tests/              # Full suite: Unit, integration, and resilience tests
├── SKILL.md            # Execution protocol (v4.0 Spec)
└── pyproject.toml      # Dependency and project index
```

---

## 🛠 Development & Validation

This project integrates standard industrial validation tools:

```bash
# Verify protocol compliance
python .agents/skills/agent-skill-creator/scripts/validate.py .

# Run security scan
python .agents/skills/agent-skill-creator/scripts/security_scan.py .

# Run all tests
pytest
```

---

## 🔒 Security & Privacy

We guarantee that **zero source code** is uploaded to third-party servers. All AST parsing, de-identification, and suggestion generation occur locally. AI agents only receive masked snippets required for translation assistance under your explicit permission.

---

## 💖 Support the Project

If you find **i18n-agent-skill** helpful, please consider:
- Giving the project a **Star** ⭐ to show your support.
- **Afdian (爱发电)**: [https://ifdian.net/a/shirolin](https://ifdian.net/a/shirolin)
- **Ko-fi**: [https://ko-fi.com/shirolin](https://ko-fi.com/shirolin)

---

## 📄 License

Licensed under [Apache-2.0](LICENSE).
