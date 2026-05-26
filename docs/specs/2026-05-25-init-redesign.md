# Intent-Driven Init Redesign

## Summary

`i18n init` currently behaves like a static config generator. It detects a locale directory, then writes a hardcoded `enabled_langs` list that can disagree with the project's real locale assets. This is a severe initialization defect because the first interaction with the skill can immediately produce misleading audit results.

This redesign changes `init` from "write starter config" into an intent-driven initializer that first inspects project facts, classifies the project's i18n state, and then chooses one of four outcomes:

- `sync`: existing local locale assets are clear and can be synchronized automatically.
- `reconcile`: the project appears to be internationalized, but there are multiple plausible interpretations that require user confirmation.
- `bootstrap`: no locale assets exist yet, but the project looks like a valid candidate for first-time i18n setup.
- `unsupported`: the project does not look compatible with the local-file locale workflow this skill assumes.

## Problem Statement

### Current defects

1. `initialize_project_config()` hardcodes `enabled_langs` to `["en", "zh"]`.
2. The config model default and init output are inconsistent (`["en", "zh-CN"]` vs `["en", "zh"]`).
3. `init --auto` does not change locale detection behavior; it only forwards a flag.
4. Existing locale files on disk are ignored during initialization.
5. Already-internationalized projects can be initialized into a broken config state on the very first run.

### Observed failure mode

For a project that already has locale files such as `en.json`, `zh_CN.json`, and `zh_TW.json`, init writes `enabled_langs: ["en", "zh"]`. Downstream audit then treats `zh` as a real target language, causing false missing-key reports while the real language packs remain healthy.

## Design Goals

- Make `init` safe for already-internationalized projects.
- Base initialization on project facts from disk, not hardcoded language defaults.
- Auto-heal stale or underspecified config only when the repair is deterministic.
- Require user confirmation when more than one valid interpretation exists.
- Support clean first-time setup for projects with no locale assets yet.
- Avoid writing misleading config when the project state cannot be classified reliably.

## Non-Goals

- No new runtime translation features.
- No support in this change for non-file-backed translation systems.
- No automatic normalization between `zh-CN` and `zh_CN`; detected language codes are preserved exactly as found on disk.
- No change to public command names in this phase.

## Project Classification Model

Initialization becomes a two-phase pipeline:

1. Detect project i18n state.
2. Materialize config only if the detected state permits it.

### Phase 1: Detection

The detector gathers these facts:

- Standard locale directory candidates: `src/locales`, `locales`, `public/locales`.
- Extended candidates: `i18n`, `translations`, `messages`, `lang`.
- Supported file extensions: `.json`, `.yaml`, `.yml`, `.ts`, `.js`.
- Locale filename stems detected under each candidate directory.
- Whether the project already has `.i18n-skill.json`.
- Whether the existing config conflicts with disk facts.
- Whether source code appears to contain extractable UI strings.

### Phase 2: Classification

The detector assigns exactly one mode:

#### `sync`

Use when:

- One locale root is clearly dominant.
- Locale filenames follow language-code-like stems.
- The detected language set is non-empty.

Behavior:

- Write or update `.i18n-skill.json`.
- Replace stale `enabled_langs` with detected languages.
- Replace stale `locales_dir` with the detected locale root.
- Preserve user-owned config fields not derived from detection.

#### `reconcile`

Use when:

- More than one candidate locale root looks valid.
- Both old config and disk facts are plausible but conflict.
- Multiple language file naming schemes coexist in a way that affects behavior.
- File format selection would influence future writes and there is no single correct answer.

Behavior:

- Do not write `.i18n-skill.json`.
- Return structured candidates and the reason confirmation is required.

#### `bootstrap`

Use when:

- No locale assets are detected.
- The project still looks like a normal app codebase that may be preparing to add i18n.

Behavior:

- Write a minimal config for first-time setup.
- Mark the result explicitly as bootstrap-based, not synchronized-from-assets.
- Prefer `src/locales` if `src` exists, otherwise `locales`.
- Do not invent non-English languages.

#### `unsupported`

Use when:

- The project appears to use a non-file-backed translation system.
- There are strong i18n signals, but they do not match a local-file locale workflow.
- Files exist, but their names are not interpretable as languages and no reliable fallback exists.

Behavior:

- Do not write `.i18n-skill.json`.
- Return a structured diagnostic explaining why the workflow is unsupported.

## Deterministic Auto-Heal Rules

These cases should be auto-corrected without asking the user:

- Existing config contains `zh`, while disk facts clearly expose `zh_CN` and `zh_TW`.
- Existing config language set is a strict subset of the detected language set.
- Existing config locale root is stale, but exactly one valid locale root exists.
- `preferred_format` is unset and all detected locale files use the same extension.

Auto-heal must produce a `migrations` list describing what changed.

## Interactive Reconciliation Rules

These cases require confirmation before any write:

- Two or more locale roots contain valid language files and neither clearly dominates.
- Language stems include both aggregate and regional variants, such as `zh` and `zh_CN`, without a deterministic rule for precedence.
- Detected file formats are mixed and selecting a single preferred write format would materially affect future behavior.
- Existing config intentionally differs from disk facts in a way that could represent user intent rather than staleness.

The response must include:

- candidate locale roots
- candidate languages per root
- candidate preferred formats
- a concise explanation of why automatic repair is unsafe

## Hard Failure Rules

Hard failure still exists, but only for unsafe or unusable states:

- The existing `.i18n-skill.json` is malformed and cannot be safely merged.
- Path validation or workspace boundary checks fail.
- A locale root is found, but the directory is unreadable.
- The detector cannot produce either a reliable candidate set or a valid bootstrap interpretation.

Hard failure does not write config.

## Config Write Rules

### Fields derived from project facts

These should be recomputed during `sync` and `bootstrap`:

- `source_dirs`
- `locales_dir`
- `enabled_langs`
- `preferred_format` when inferred deterministically

### Fields preserved from existing config

These should survive a `sync` rewrite unless invalid:

- `privacy_level`
- `persona`
- `protected_lang_key_patterns`
- `ignored_keys`
- `ignored_strings`
- `ignore_dirs`
- `locale_file_pattern`
- `preferred_format` when already set and still compatible with detected files

## Output Contract

`init` should return structured data that explains what happened, not just the resulting config.

Required top-level fields:

- `mode`: `sync | reconcile | bootstrap | unsupported | hard_fail`
- `message`
- `config`: present only when a config was written
- `detected_locale_dirs`
- `detected_locale_files`
- `detected_languages`
- `migrations`
- `warnings`
- `requires_confirmation`
- `suggested_action`

### Example outcomes

- `sync`: config written, stale `zh` replaced with detected language list.
- `reconcile`: no config written, response contains candidate directories and languages.
- `bootstrap`: config written with a minimal initial language set, typically only `en` if no locale assets exist.
- `unsupported`: no config written, response explains that the project does not match file-based locale assumptions.

## Detection Details

### Locale root selection

Priority should not rely only on a static directory order. Selection should combine:

- whether supported locale files exist
- how many languages are detected
- whether `en` is present
- whether an existing config points to the same directory

If exactly one candidate is clearly stronger by these signals, use it. Otherwise enter `reconcile`.

### Language detection

Language detection should be based on filename stems of supported files, for example:

- `en.json` -> `en`
- `zh_CN.ts` -> `zh_CN`
- `pt_BR.yml` -> `pt_BR`

The detector should not invent aliases or normalize separators in this phase.

### Bootstrap heuristics

Bootstrap is allowed only if:

- no locale root with supported language files was found
- the project contains source code suitable for scanning
- the project is not already obviously configured for a non-file-based translation flow

Bootstrap should not claim that languages were detected.

## Testing Plan

Add coverage for these scenarios:

1. Existing multi-language project:
   - `src/locales` contains `en.json`, `zh_CN.json`, `zh_TW.json`, `fr.json`, `ja.json`.
   - init enters `sync`.
   - config contains the full detected language set.

2. Stale config migration:
   - existing config has `enabled_langs: ["en", "zh"]`.
   - disk contains `en.json`, `zh_CN.json`, `zh_TW.json`.
   - init rewrites config and reports a migration.

3. Single-root deterministic repair:
   - config points to `locales`, but only `src/locales` contains valid locale files.
   - init rewrites `locales_dir` automatically.

4. Multiple-root conflict:
   - both `src/locales` and `public/locales` contain plausible but different language sets.
   - init enters `reconcile`.
   - no config file is written.

5. Bootstrap:
   - no locale assets exist.
   - `src` exists and contains app code.
   - init writes a minimal bootstrap config and marks `mode: bootstrap`.

6. Unsupported:
   - translation artifacts exist, but do not follow a file-backed locale pattern.
   - init returns `unsupported`.

7. Malformed existing config:
   - init returns hard failure and preserves the broken file for manual recovery.

8. Preservation:
   - existing config contains persona and ignore rules.
   - sync rewrite preserves them.

## Rollout Notes

- This redesign should be implemented before any further init-related UX polish.
- The README should be updated after implementation so that `init` is described as a project-aware synchronization/bootstrap step, not a static config generator.
- The current roadmap item for `--auto` should be revised because `--auto` is not the main issue; the main issue is base init classification and detection.
