---
Status: active
Owner: CT
Created: 2026-06-10
Last verified: 2026-07-14
Kind: process
---

# Lint deviations

## Agent Index

- **Kind:** process
- **Status:** active
- **Read when:** adding, removing, or auditing static-analysis suppressions.
- **Search terms:** Ruff, basedpyright, ESLint, suppression, ignore, noqa.

This is the single catalogue for intentional Python and frontend static-analysis
exceptions. Inline exceptions must also state why they are safe.

## Ruff configuration

`pyproject.toml` globally ignores rules whose repository-wide use is deliberate:
`B008`, `UP042`, `E501`, `D203`, `D212`, `D100`, `D104`, `D107`, `PLR0913`,
`PLR2004`, `TRY003`, `COM812`, `PLC0415`, `PLR0912`, `PLR0911`, `PLR0915`,
`ANN401`, `D205`, and `D105`. These cover FastAPI dependency defaults, enum
compatibility, formatter/docstring conflicts, generated or inherited long lines,
complexity in orchestration boundaries, and the repository's terse docstring
policy.

Per-file groups narrow noisy rules at established boundaries:

- `tests/*`: test assertions, fixtures, test constants, subprocess helpers,
  intentionally broad annotations, and failure-path exercises.
- `scripts/*.py` and `build_hooks/*.py`: command output, subprocess execution,
  and small operational entry points.
- `**/__init__.py`, `**/_*.py`, and `src/.../__main__.py`: package exports,
  generated/private modules, and the CLI boundary.

## Python inline suppressions

- `TC001`, `TC002`, and `TC003` in `core/models.py`, `core/app_state.py`,
  `domain/labeler_export.py`, and API model modules keep Pydantic or FastAPI
  annotation symbols available at runtime.
- `BLE001` and `S110` in `bootstrap.py`, `worker/train.py`,
  `worker/evaluate.py`, `api/ui_prefs.py`, and
  `adapters/dataset_sources/huggingface.py` make optional probes, worker error
  envelopes, corrupt preferences, and remote preview failure-safe.
- `N815` in `api/ui_prefs.py` preserves the frontend's camelCase wire contract.
- `S202` in `tests/test_packaging.py` extracts only the test-built archive into
  a temporary directory.
- `I001` and basedpyright optional-import exceptions in
  `domain/labeler_export.py` preserve boot compatibility with older
  `pdomain-ops` wheels while providing typed fallbacks.
- `reportReturnType` in `adapters/builders.py` and `reportGeneralTypeIssues` in
  `api/jobs.py` cover the upstream `LongJobRunner.stream_events` Protocol shape:
  implementations are async generators although the Protocol presents the call
  as returning an iterator.
- Optional `pdomain-ops` device-probe imports in `bootstrap.py` use
  `reportMissingImports`; startup remains valid without that optional surface.
- Test `type: ignore[arg-type]` annotations in `tests/conftest.py`,
  `tests/test_ui_prefs.py`, `tests/test_routes_root.py`,
  `tests/unit/test_settings.py`, `tests/unit/api/test_datasets_diagnostics.py`,
  `tests/unit/domain/test_labeler_export.py`,
  `tests/unit/training/test_worker_dispatch.py`,
  `tests/e2e/test_labeler_freshness.py`, and
  `tests/e2e/test_m12_typeface.py` cover Pydantic `Path` inputs and deliberate
  protocol fakes that runtime validation accepts.
- Test `type: ignore[assignment]`, `type: ignore[return]`, and
  `type: ignore[union-attr]` annotations in
  `tests/unit/domain/test_labeler_export.py` and
  `tests/unit/adapters/test_dataset_sources.py` cover temporary optional-import
  monkeypatches and fixtures whose concrete row variant is known.
- Test `type: ignore[attr-defined]` annotations in
  `tests/integration/api/test_runs.py`, `tests/slow/test_eval_worker_e2e.py`, and
  `tests/slow/test_stub_worker_e2e.py` exercise runtime-installed FastAPI state
  and concrete runner helpers omitted from their static interfaces.
- Test `type: ignore[no-untyped-def]` annotations in
  `tests/e2e/test_m12_typeface.py` cover pytest and Playwright fixtures that do
  not expose useful static types. `type: ignore[arg-type]` in
  `tests/unit/adapters/test_auth.py` confirms that the no-auth adapter safely
  ignores its request value. These test-only annotations do not relax
  production checking.

## ESLint configuration

`frontend/eslint.config.js` excludes generated output, dependencies, test files,
and tooling config from the type-aware application pass. It disables
`@typescript-eslint/array-type`, `no-confusing-void-expression`, and
`prefer-nullish-coalescing`. These are style choices, not correctness gates; the
codebase intentionally mixes array notation, uses void expressions in UI
callbacks, and distinguishes some falsy values explicitly.

## Frontend inline suppressions

- `no-misused-spread` in the internal request helpers in `api/datasets.ts`,
  `api/eval.ts`, `api/models.ts`, `api/profiles.ts`, and `api/runs.ts`: callers
  pass record headers, never a `Headers` instance.
- `no-dynamic-delete` in `stores/datasetsStore.ts`: the key comes from the
  store's own staged-record key set and deletion performs cache invalidation.
- `no-deprecated` in `shell/TrainerHeader.tsx` and `shell/useTrainerJobs.ts`:
  upstream declaration JSDoc falsely marks `ActiveJob` deprecated.
- `no-empty-function` in `shell/useTrainerShortcuts.ts`: the callback exists
  only to register a display-only shortcut.
- `react-hooks/exhaustive-deps` in `pages/NewRunPage.tsx`,
  `pages/EvalFormPage.tsx`, and `hooks/useNotificationStream.ts`: the first two
  initialize once on mount; the stream uses a stable content signature instead
  of the jobs array identity.
- `react-refresh/only-export-components` in `components/AppToaster.tsx`:
  `emitToast` is a public driver-contract helper colocated with its renderer.

## Audit method

The 2026-07-14 audit searched Python, TypeScript, TSX, `pyproject.toml`, and
`frontend/eslint.config.js` for `noqa`, type/basedpyright ignores, ESLint
disable comments, global ignores, and per-file ignores. Mypy-style production
fallback ignores in `bootstrap.py` and `domain/labeler_export.py` were replaced
with basedpyright-native rule names. Test-only mypy-style annotations remain
because Ruff and pytest tooling also consume those explicit test adaptations.
