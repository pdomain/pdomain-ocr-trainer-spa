---
Status: active
Owner: CT
Created: 2026-07-14
Last verified: 2026-11-06
Kind: architecture
---

# Trainer workflows

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** changing trainer workflows, jobs, the shared shell, or quality
  gates.
- **Search terms:** profiles, kanban, runs, jobs, SSE, pdomain-ui, ESLint.

The SPA keeps its FastAPI web process free of Torch.

It builds typed run configuration.

It delegates long work to worker subprocesses through `pdomain-ops`.

The React application provides profile, dataset, run, evaluation, model, and publishing screens over those APIs.

## Dataset, training, and evaluation flow

Profiles select local dataset roots and training defaults.

Dataset APIs build kanban views for detection, recognition, and typeface-classification data.

Training and evaluation create run records, submit jobs, and expose progress and results through the jobs and run APIs.

The jobs surface requires `GET /api/jobs`.

Each mapped job carries its `progress` and associated `run_id` so the shared dock can open the run.

Detection and recognition training call `LocalTrainingRunner`. Typeface training does not.

The worker builds a local `TypefaceConfig` and calls `train_typeface` through a cast.

The real runner does not provide `train_typeface`.

`FakeTrainingRunner` covers that seam in tests.

The production eval worker does not call `LocalEvalRunner`.

`worker/evaluate.py` `_build_runner` raises `RuntimeError` until upstream eval accepts glyph annotations and fills slices.

Tests inject a stub runner.

## Shared application shell

The frontend uses `@pdomain/pdomain-ui ^0.11.0` with React 19.

`AppShell` provides the rail and utility dock.

Trainer-owned adapters supply header, shortcut, compute-target, and jobs content.

The two surfaces coexist by design. The notification SSE stream still drives transient notices while the polling jobs adapter supplies durable dock state.

## Hugging Face boundaries

Read and publish capabilities are gated separately. Dataset-source reads do not imply permission to publish models or datasets. Publishing remains an explicitly enabled write path.

## Lint and type gates

The Python gate uses Ruff and basedpyright.

The frontend package's `lint` script runs ESLint with `--max-warnings 0`. This gate lives in the frontend package rather than a repository-global ESLint command.

The single [lint deviations catalogue](../conventions/lint-deviations.md) records configured rule exceptions and inline suppressions.

## Checked code, tests, and configuration

- Code: `src/pdomain_ocr_trainer_spa/api/`,
  `src/pdomain_ocr_trainer_spa/domain/`,
  `src/pdomain_ocr_trainer_spa/training/config_build.py`,
  `src/pdomain_ocr_trainer_spa/training/fake_runner.py`,
  `src/pdomain_ocr_trainer_spa/worker/train.py`,
  `src/pdomain_ocr_trainer_spa/worker/evaluate.py`, `frontend/src/App.tsx`,
  and `frontend/src/shell/`
- Tests: `tests/integration/api/`, `tests/unit/training/`,
  `tests/unit/worker/test_evaluate.py` (`test_build_runner_surfaces_upstream_gap`),
  `tests/unit/domain/test_datasets.py` (`test_glyph_classifier_task_still_rejected`),
  `tests/e2e/test_m12_typeface.py`, `tests/e2e/test_shell_migration.py`, and
  `frontend/src/shell/*.test.tsx`
- Configuration: `pyproject.toml`, `frontend/eslint.config.js`, and
  `frontend/package.json`
- Verified: 2026-11-06 by reading the worker, config, and named tests
