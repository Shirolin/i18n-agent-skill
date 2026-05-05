# Tree-sitter AST Extraction Engine

`i18n-agent-skill` leverages the **Tree-sitter AST (Abstract Syntax Tree)** parsing engine instead of traditional RegEx matching. This is the core reason why this project achieves 100% comment isolation and high-precision extraction.

## Why Refuse RegEx?

Regular expressions have fatal flaws when processing frontend code:
1. **Comment Misidentification**: Difficulty in distinguishing between strings in code and those within comments (e.g., `// console.log("todo")`).
2. **Nesting Challenges**: Difficulty in handling complex nested template literals.
3. **Missing Context**: RegEx cannot understand if a string is within a JSX attribute, a text node, or a regular logic variable.

## How the AST Engine Works

1. **Multi-language Parsing**: Supports parsing syntax trees for `typescript`, `tsx`, `vue`, `javascript`, and more.
2. **Depth-First Traversal**: Traverses the syntax tree using Depth-First Search (DFS).
3. **Node Filtering**: 
   - Extracts `string` objects.
   - Extracts `template_string` (including nested `${}` expressions).
   - Extracts `jsx_text` in JSX.
   - Extracts text nodes in Vue templates.
4. **Attribute Awareness**: Identifies and filters specific attributes (e.g., `className`, `id`, `style`), preventing non-text attributes from being extracted as translation units.

## Technical Metrics
- **Parsing Speed**: Millisecond-level.
- **Accuracy**: 100% syntax-level accuracy; no missing or incorrect extractions.
## Connection to Lifecycle

The AST Engine is the primary driver for **Phase 2: Discovery**. It provides the deterministic raw material (L1 Drafts) that is later refined by the project persona and human oversight.
