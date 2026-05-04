# Product Scenarios & Authority Hierarchy 🗺️

This document defines the core business logic and the "Hierarchy of Authority" that drives the **i18n-agent-skill** ecosystem. It serves as the ultimate reference for maintaining architectural integrity during future iterations.

---

## ⚖️ The Hierarchy of Authority (Weight System)

To ensure high-quality evolution, the system treats different translation sources with varying levels of trust and persistence.

| Level | Name | Source | Status | System Logic |
| :--- | :--- | :--- | :--- | :--- |
| **L1** | **Draft** | Raw `/i18n-scan` (AI) | `DRAFT` | Temporary first-draft. High flexibility, subject to overwrite during optimization. |
| **L2** | **Policy** | `/i18n-optimize` + **Human Commit** | `APPROVED` | **Core Production Engine**. Represents a human-verified AI suggestion aligned with the project persona. |
| **L3** | **Truth** | **Manual File Edits** + `/i18n-learn` | `APPROVED` | **Absolute Truth**. Hard-coded human intent (e.g., UI layout fixes). Locked against future AI overrides. |

---

## 🔄 The 5-Phase Business Lifecycle

### Phase 1: Zero-Friction Handshake (The Persona)
- **Goal**: Align the AI's "brain" with the project's "soul."
- **Scenario**: Upon cloning, the AI assistant runs `/i18n-init`. The system returns project metadata (README, package.json).
- **The Handshake**: AI proposes a project persona (e.g., "Medical, Professional"). User confirms. This establishes the global tone for all future work.

### Phase 2: Inventory & Discovery (L1 Baseline)
- **Goal**: Map the unknown and establish a starting point.
- **Scenario**: On a new feature or a chaotic legacy project, AI runs `/i18n-scan` and `/i18n-audit`.
- **Result**: Identifies leaked hardcoded strings and "Dead Keys" (unreferenced translations), creating an L1 `DRAFT` inventory.

### Phase 3: Quality Wash & Promotion (L2 Policy)
- **Goal**: Transform "machine-speak" into "brand-speak."
- **Scenario**: User triggers `/i18n-optimize`. AI uses the Persona defined in Phase 1 to rewrite the inventory.
- **The Promotion**: User reviews the Markdown preview and runs `/i18n-commit`. The system automatically promotes these entries to `APPROVED` (L2).

### Phase 4: Semantic Projection (Pivot-Sync)
- **Goal**: Achieve global consistency with zero redundant effort.
- **Scenario**: Once the primary language (e.g., Japanese) is at L2 quality, user triggers `/i18n-pivot-sync`.
- **Logic**: The system only uses `APPROVED` keys as anchors to project the verified semantics onto other languages (e.g., French, German).

### Phase 5: Absolute Truth Recovery (L3 Mastery)
- **Goal**: Honor human edge-case requirements.
- **Scenario**: A user manually shortens a word in `fr.json` to prevent a button overflow.
- **The Evolution**: User runs `/i18n-learn`. The system detects the physical change, grants it L3 `APPROVED` status, and learns this terminology for the project's permanent glossary.

---

## 🧩 Architectural Intent
1. **Persona First**: No translation happens in a vacuum. Tone is a configuration, not a guess.
2. **Commit is Approval**: A human `commit` is a semantic act, not just a file write.
3. **Data is Fluid, Truth is Static**: Automated L1/L2 flows handle 99% of the volume; L3 handles the 1% human nuance.
