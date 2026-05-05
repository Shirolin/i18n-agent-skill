# Privacy Guard Masking Mechanism

Security is the primary consideration when performing i18n extraction and translation synchronization tasks. `i18n-agent-skill` integrates a high-strength privacy masking mechanism to ensure that sensitive information does not leak to the LLM translation backend.

## Core Masking Logic

The privacy_guard performs the following scans before data leaves the local environment:

1. **Credential Scanning**:
   - Matches common API Keys (OpenAI, AWS, GitHub, etc.).
   - Matches database connection strings (Data Source Names).
   - Matches hardcoded passwords and tokens.

2. **PII Recognition (Personally Identifiable Information)**:
   - Identifies and masks email addresses.
   - Identifies and masks phone numbers.
   - Identifies and masks internal private IP addresses.

3. **Path Sensitivity**:
   - Automatically removes local absolute paths, retaining only relative paths relative to the project root.

## Masking Methods

- **Hashing**: Key identifiers are replaced with irreversible hash values, maintaining consistency in contextual references.
- **Placeholder Replacement**: Sensitive information is replaced with specific placeholders (e.g., `[MASKED_EMAIL]`, `[MASKED_API_KEY]`).

## Compliance Tips
## Connection to Lifecycle

Privacy Guard operates silently during **Phase 2 (Discovery)** and **Phase 3 (Promotion)**. It ensures that the "AI Labor" part of the cycle remains within security boundaries, making the "Human-in-the-loop" experience safe for enterprise use.
