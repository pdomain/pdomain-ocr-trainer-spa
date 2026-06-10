# Lint Deviations

This document records intentional suppressions of static-analysis warnings
that are approved by convention. Each entry names the rule, the tool, the
affected files, and the justification.

---

## `domain/labeler_export.py`: optional pdomain-ops Track-B imports

- **Rules:** `reportMissingImports` (basedpyright), `no-redef` / `misc`
  (pyright `type: ignore` annotations), `noqa: I001` (ruff import-order)
- **Tool:** basedpyright + pyright type annotations + ruff
- **Files:** `src/pdomain_ocr_trainer_spa/domain/labeler_export.py`
- **Justification:** Track B (`pdomain-ops`) adds `resolve_shared_path` and
  `DoctrExportManifest` / `read_manifest`. The SPA must boot with a pre-Track-B
  wheel installed; the `try/except ImportError` guard plus fallback stubs is the
  approved pattern. Inline `# pyright: ignore[...]` and `# type: ignore[...]`
  comments name the suppressed codes at each deviation site.
- **Note on F811 / redefinition:** ruff F811 ("redefinition of unused name") is
  NOT suppressed because ruff does not flag the `except ImportError` fallback
  definitions as F811 in this pattern (they are in separate branches). The
  `# type: ignore[no-redef]` annotation on the fallback `DoctrExportManifest`
  class is for mypy / basedpyright only.

---

## Frontend ESLint deviations (Track F)

### `@typescript-eslint/no-dynamic-delete`

- **Files:** `frontend/src/stores/datasetsStore.ts:108`
- **Justification:** Deliberate cache-key invalidation. `pageKey` is always a
  string key from the store's own `staged: Record<string, KanbanColumnId>`
  record type. The rule is promoted to `error`; this single site is suppressed
  with an inline `// eslint-disable-next-line` comment.

### `@typescript-eslint/no-deprecated` — `ActiveJob` false positive

- **Files:** `frontend/src/shell/TrainerHeader.tsx:7`,
  `frontend/src/shell/useTrainerJobs.ts:3,6`
- **Justification:** `ActiveJob` is not itself deprecated. Its JSDoc block
  comment in the pdomain-ui type declarations is shared with the deprecated
  `JobsPill` props block, causing the rule to flag the type as deprecated.
  This is a false positive from upstream `@pdomain/pdomain-ui` declaration
  formatting. Suppressed with inline comments at each usage site until
  pdomain-ui corrects the JSDoc layout.

### `@typescript-eslint/array-type` — kept `off`

- **Files:** `frontend/eslint.config.js`
- **Justification:** Existing code mixes `T[]` and `Array<T>`. Enabling this
  rule as `error` requires a style decision that is deferred — not in scope
  for Track F.
