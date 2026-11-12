---
Status: active
Owner: CT
Created: 2026-07-14
Last verified: 2026-11-12
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

The React application provides profile, dataset, run, evaluation, model, and publish screens over those APIs. Publish screens do not upload yet. See [Hugging Face read and publish](huggingface.md).

## Dataset, training, and evaluation flow

Profiles select local dataset roots and training defaults.

Dataset APIs build kanban views for detection, recognition, and typeface-classification data.

Training and evaluation create run records, submit jobs, and expose progress and results through the jobs and run APIs.

The jobs surface requires `GET /api/jobs`.

Each mapped job carries `progress` (0–1) and `run_id`. The dock opens `/runs/` with the job id, not `run_id`.

The production worker builds `LocalTrainingRunner`. Detection and recognition
dispatch call its typed methods.

The worker builds a local `TypefaceConfig` and calls `train_typeface` through a cast.

The SPA does not verify that the production runner provides `train_typeface`;
its typed runner interface covers only detection and recognition.

`FakeTrainingRunner` covers that seam in tests.

The production eval worker does not call `LocalEvalRunner`.

`worker/evaluate.py` `_build_runner` raises `RuntimeError`. The text inside that raise is stale against `pdomain-ocr-training` 0.2.1, which already has the glyph-slice fields. Details are in [runs and evaluation](runs-and-evaluation.md).

Tests inject a stub runner.

## Shared application shell

The frontend uses `@pdomain/pdomain-ui ^0.12.1` with React 19.

`AppShell` provides the rail and utility dock.

Trainer-owned adapters supply header, shortcut, compute-target, and jobs content.

The jobs dock polls `GET /api/jobs`. Run detail opens the job SSE stream.

Terminal toasts do not fire. `App.tsx` does not call `useNotificationStream`. A sonner toaster is mounted, and `useNotificationStream` can toast terminal events. Details are in [shell, jobs, and the client contract](shell-and-jobs.md).

## Where to read the rest

- [Profiles, datasets, and models](profiles-datasets-and-models.md)
- [Runs and evaluation](runs-and-evaluation.md)
- [Shell, jobs, and the client contract](shell-and-jobs.md)
- [Hugging Face read and publish](huggingface.md)
- [Labeler import and freshness](labeler-import-and-freshness.md)

## Hugging Face boundaries

Dataset preview uses the token file. Publish routes validate the token and the license, then the domain helper raises `AdapterNotImplementedError`. `enable_hf_publish` is copied onto `/env.js` and does not gate those routes. A successful preview does not upload.

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
- Verified: 2026-11-07 by reading the worker, config, and named tests;
  application tests were not rerun for this documentation check
