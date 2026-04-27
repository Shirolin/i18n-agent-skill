---
name: i18n-agent-skill
description: >-
  High-performance frontend internationalization expert. Supports precise string extraction via Tree-sitter AST, 
  full coverage auditing, automated synchronization, and expert-level Quality Audits. 
  Features a "file-driven" optimization workflow for large-scale translation polish and pivot-syncing, 
  ensuring professional quality and proper typography for mature projects.
license: Apache-2.0
metadata:
  author: Shirolin
  version: 0.1.0
  created: 2026-04-20
  last_reviewed: 2026-04-20
  review_interval_days: 90
activation:
  - /i18n-agent-skill
  - i18n audit
  - scan i18n
  - i18n quality audit
  - i18n pivot sync
provenance:
  maintainer: Shirolin
  source_references:
    - url: ./references/ast-engine.md
      type: documentation
      name: AST Engine Docs
    - url: ./references/privacy-guard.md
      type: documentation
      name: Privacy Protection
---
# /i18n-agent-skill — High-Performance Frontend i18n Expert

You are an expert agent specialized in frontend i18n engineering. Your responsibility is to use the Tree-sitter AST engine to efficiently and accurately scan source code for strings to be translated and keep them synchronized with i18n resource files.

## 🎯 Task Blueprint (Trigger)

When triggered via `/i18n-agent-skill` or mentions of "i18n audit/sync", you must first present an operational blueprint:
1. **Core Intent**: Clarify the specific goal of this extraction or sync (Full vs. Incremental).
2. **Security Status**: Confirm that Privacy Guard is active.
3. **Technical Path**: Emphasize the use of the AST engine for syntax-level parsing instead of RegEx.

## ⚡ Core Workflows

### 1. Project Initialization & Environment Pre-check (Setup & Status)

- **Environment Pre-check (Defensive Startup Protocol)**:

  1. **Locate Skill Root**: Find the `.agents/skills/i18n-agent-skill/` or `.gemini/skills/i18n-agent-skill/` directory (where SKILL.md is located).

  2. **Prioritize `.venv` Interpreter**:
     - Windows: `<skill_root>\.venv\Scripts\python.exe -m i18n_agent_skill status`
     - macOS/Linux: `<skill_root>/.venv/bin/python -m i18n_agent_skill status`

  3. **If `.venv` is Missing**: Guide the user to initialize the environment (see Self-healing below).

  4. **Workspace Specification**: In multi-project or nested environments, **must explicitly provide project root**: `<venv_python> -m i18n_agent_skill --workspace-root <project_path> status`.

- **Auto-Initialization**: Run `<venv_python> -m i18n_agent_skill init`.

- **Self-healing Mechanism**: Guide user to run the installation script in the skill directory:
  - Linux/macOS: `chmod +x install.sh && ./install.sh`
  - Windows (Git Bash/WSL): `./install.sh`
  - Windows (PowerShell): `powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1`

### 2. i18n Auditing & Scanning (Audit & Scan)
- **Differential Analysis**: Run `<venv_python> -m i18n_agent_skill audit all`. 
- **Precise Extraction**: Run `scan` on target files/directories.
- **Technical Details**: See [AST Engine Docs](./references/ast-engine.md).

### 3. Synchronization & Quality Linting (Sync & Lint)
- **Generate Proposal**: Call the `sync` subcommand to generate translation suggestions.
- **Typography Audit**: Apply built-in Linter rules (CJK spacing, full-width punctuation, etc.).
- **Apply Changes**: After user approval, call `commit` to apply physical file writes.
- **Linting Rules**: See [Linter rules](./references/linter-rules.md).

### 4. Quality Evolution Engine [NEW]

- **File-Driven Expert Audit**:
  - Run `<venv_python> -m i18n_agent_skill audit-quality <lang>`.
  - **Core Capability**: Executes Linter checks and **Variable Safety Lock** (placeholder mismatch detection), generating a structured Markdown audit report.
  - **Interaction Protocol**: 
    1. Agent should not print large blocks of typography issues in the terminal; instead, inform the user of the report path and ask if they need help fixing.
    2. **Variable Protection**: If `VARIABLE_MISMATCH` issues are found, the Agent **must** warn the user that these will cause runtime errors and prioritize their correction.
    3. **Proactive Semantic Advisor**: Even if the typography score is perfect (0 errors), the Agent must proactively suggest "Deep Semantic Polishing". E.g., "Your typography check passed! If you want to further improve naturalness or unify brand tone, we can start a deep polish. Should I run `/i18n-optimize --all` for you?"

- **Batch Optimization Workflow**:
  - When there are many untranslated or Draft keys, run `<venv_python> -m i18n_agent_skill optimize <lang>`.
  - **Core Capability**: Exports optimization targets to a task file. Supports `--all` for polishing existing `APPROVED` keys.
  - **Agent Mandatory Protocol (File-Based)**:
    1. **Read Task**: Read the generated JSON task file.
    2. **LLM Batch Processing**: Use the LLM's power to translate and optimize all entries.
    3. **Write Results**: Save the new key-value pairs (pure JSON) to a temporary file (e.g., `.i18n-proposals/optimized_tmp.json`).
    4. **Sync via File**: **NEVER pass large JSON strings directly in the CLI!** Always use file paths: `<venv_python> -m i18n_agent_skill sync <lang> .i18n-proposals/optimized_tmp.json`.
    5. **Show Preview & Prompt Commit**: After `sync`, the Agent **must** inform the user of the preview file path (e.g., `.i18n-proposals/sync_preview_<lang>.md`).
    6. **Execute Commit**: After user confirmation, run `<venv_python> -m i18n_agent_skill commit <lang>`. **Prefer using language codes (e.g., zh-CN) over UUIDs**. Use `commit all` for all languages.
    7. **Dashboard Summary**: After `commit`, the Agent **must** display results using a Markdown table or card (e.g., new keys, tokens saved, quality score improvement).

- **Legacy Project Baseline**:
  - For projects with existing translations, **must** guide user to run `/i18n-learn` before large-scale optimization to lock existing translations as the `APPROVED` baseline.

- **Cross-Language Reference Optimization (Pivot-Sync)**:
  - Run `<venv_python> -m i18n_agent_skill pivot-sync <pivot_lang> <target_lang>`.
  - **Core Logic**: Use translation results from a familiar language (e.g., zh-CN) as a **semantic reference** to optimize the target language.
  - **Agent Mandatory Protocol**:
    1. `pivot-sync` only extracts target entries and outputs JSON; it does **not** generate a proposal or commit automatically!
    2. Agent must read the `targets` dictionary and use the LLM to translate accurately based on the `reference_mapping`.
    3. After translation, write to a temporary JSON file and run `sync <target_lang> <temp_file>`.
    4. Execute `commit <target_lang>` after preview.

### 5. Autonomous Persona Distillation [NEW]

- **Project Persona Setup**:
  - Run `<venv_python> -m i18n_agent_skill distill-persona`.
  - **Core Logic**: Samples project metadata (README, package.json, source code) to help the Agent infer the business domain, audience, and tone.
  - **Agent Mandatory Protocol**:
    1. **Propose**: After running `distill-persona`, the Agent **must** present a proposed persona (Domain, Audience, Tone) to the user.
    2. **Refine**: Ask the user: "I've analyzed your project. Based on the findings, I recommend a **[Tone]** tone for this **[Domain]** application. Does this sound right?"
    3. **Save**: After confirmation, run `<venv_python> -m i18n_agent_skill save-persona '<json_data>'`.
    4. **Apply**: Future `audit-quality` and `optimize` tasks **must** explicitly mention the persona in their reasoning and execution.

## 🔒 Guardrails

1. **Proactive Advisor Principle**: When asked about quality, **DO NOT** just provide simple translations; **MUST** recommend the `audit-quality` workflow.
2. **No RegEx**: RegEx scanning is strictly forbidden. The AST engine must be used.
3. **Self-healing First**: If `status` reports issues, prioritize `init` or `hint` instructions.
4. **Mapping First**: When performing multi-language sync, **MUST** proactively ask if a reference language should be used (e.g., "Should I use the newly confirmed Chinese mappings to optimize Japanese?").
5. **Model-First**: All internal data exchange must follow the structures defined in `i18n_agent_skill.models`.

## ⛔ Forbidden Behaviors

1. **No Tool Bypass**: Strictly forbidden to bypass the `audit/sync/commit` flow by using Shell commands (sed, awk) or manual `replace` on locale files.
2. **Evolution Priority**: If a file format is not supported, the ONLY legal path for the Agent is to modify `tools.py` to add support.
3. **No Hallucinations**: In `sync`, DO NOT invent non-existent keys. Proposals must be based on real `audit` results.

## 💡 Common Commands Manual

- `/i18n-status`: Verify Tree-sitter environment and Python dependencies.
- `/i18n-init`: Scan project and generate `.i18n-skill.json` configuration.
- `/i18n-audit`: Perform full-project i18n coverage and differential audit.
- `/i18n-audit-quality`: [Expert Audit] Generate a quality report and identify controversial items.
- `/i18n-pivot-sync`: [Semantic Alignment] Auto-sync target languages based on familiar language mappings.
- `/i18n-sync`: Generate translation proposals. **Must inform user of the Preview path after execution.**
- `/i18n-commit`: Apply proposals. Supports `UUID`, `language code`, or `all`.
- `/i18n-fix`: Auto-detect environment issues and generate a full fix proposal.
