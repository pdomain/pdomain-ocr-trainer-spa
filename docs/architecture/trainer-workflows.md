---
Status: active
Owner: CT
Created: 2026-07-14
Last verified: 2026-07-14
Kind: architecture
---

# Trainer workflows

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** changing trainer workflows, jobs, the shared shell, or quality
  gates.
- **Search terms:** profiles, kanban, runs, jobs, SSE, pdomain-ui, ESLint.

The SPA keeps its FastAPI web process free of Torch. It builds typed run
configuration and delegates long work to worker subprocesses through
`pdomain-ops`. The React application provides profile, dataset, run, evaluation,
model, and publishing screens over those APIs.

## Dataset, training, and evaluation flow

Profiles select local dataset roots and training defaults. Dataset APIs build
kanban views for detection, recognition, and typeface-classification data.
Training and evaluation create run records, submit jobs, and expose progress and
results through the jobs and run APIs. The jobs surface requires
`GET /api/jobs`; each mapped job carries its `progress` and associated `run_id`
so the shared dock can open the run.

The implementation did not follow the original milestone order exactly.
Cross-cutting shell, labeler freshness, and quality work landed alongside later
workflows. The typeface browser seam is available, but production
`TypefaceConfig`, `train_typeface`, and real typeface evaluation remain an
upstream and integration gap. Browser and API tests do not establish that
production training round-trip.

## Shared application shell

The frontend uses `@pdomain/pdomain-ui ^0.11.0` with React 19. `AppShell`
provides the rail and utility dock. Trainer-owned adapters supply header,
shortcut, compute-target, and jobs content. The notification SSE stream still
drives transient notices while the polling jobs adapter supplies durable dock
state; the two surfaces coexist by design.

## Hugging Face boundaries

Read and publish capabilities are gated separately. Dataset-source reads do not
imply permission to publish models or datasets. Publishing remains an explicitly
enabled write path.

## Quality enforcement

The Python gate uses Ruff and basedpyright. The frontend package's `lint` script
runs ESLint with `--max-warnings 0`; configured rule exceptions and inline
suppressions are recorded in the single
[lint deviations catalogue](../conventions/lint-deviations.md). This gate lives
in the frontend package rather than a repository-global ESLint command.

## Evidence

- Code: `src/pdomain_ocr_trainer_spa/api/`,
  `src/pdomain_ocr_trainer_spa/domain/`,
  `src/pdomain_ocr_trainer_spa/training/`, `frontend/src/App.tsx`, and
  `frontend/src/shell/`
- Tests: `tests/integration/api/`, `tests/unit/training/`,
  `tests/e2e/test_m12_typeface.py`, `tests/e2e/test_shell_migration.py`, and
  `frontend/src/shell/*.test.tsx`
- Configuration: `pyproject.toml`, `frontend/eslint.config.js`, and
  `frontend/package.json`
- Verified: 2026-07-14 by migration-time source and test inspection
