# Multi-language Typography & Linter Rules

To improve translation quality and UI reading experience, `i18n-agent-skill` includes built-in Quality Linting rules based on language families.

## 1. CJK Language Rules (Chinese, Japanese, Korean)

### Mixed Spacing
- **Rule**: A space is recommended between East Asian characters (Hanzi, Kana, Hangul) and Latin letters or digits.
- **Purpose**: Reduces visual density and conforms to modern CJK typography standards (e.g., "Requirements for Chinese Text Layout").
- **Example**: `Found 10 files` -> `Found 10 files` (Note: for CJK this would be `扫描到 10 个文件`).

### Full-width Punctuation
- **Rule**: In Chinese context, replacing half-width commas `,` with full-width commas `，` is recommended.
- **Purpose**: Maintains visual consistency and avoids awkward gaps in sentences.

## 2. Latin Language Rules (English, French, German, Italian, etc.)

### Consecutive Spaces
- **Rule**: Detects two or more consecutive spaces and suggests merging them into one.
- **Purpose**: Corrects extra spaces often introduced by machine translation or string concatenation.

### Punctuation Spacing
- **Rule**: A space should follow punctuation marks like periods `.`, commas `,`, colons `:`, and question marks `?` if they are followed by a letter.
- **Purpose**: Conforms to standard Western typographic conventions.
- **Note**: This rule automatically ignores decimals in numbers (e.g., `3.14`).

## How to Apply Fixes
## Connection to Lifecycle

Linter rules are enforced during **Phase 3 (Promotion)** and **Phase 5 (Mastery)**. They provide the objective standards used during the `/i18n-audit-quality` phase to justify why a translation needs further refinement.
