---
Status: active
Owner: CT
Created: 2026-05-21
Last verified: 2026-11-07
Kind: process
---

# Development Guide — pdomain-ocr-trainer-spa

## Agent Index

- **Kind:** process
- **Status:** active
- **Read when:** setting up, running, testing, or packaging the application.
- **Search terms:** development, setup, dynamic port, build, coexistence.

FastAPI + React/Vite SPA that replaces the legacy `pdomain-ocr-training`
NiceGUI UI. Detection and recognition training use the production runner.
Typeface UI and test support exist, but production typeface training and
evaluation remain unfinished. Glyph-classifier training is not implemented.

---

## Quick start

### Prerequisites

- Python 3.13 (via mise or system)
- Node 24 (via mise or system)
- uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- mise (`curl https://mise.run | sh`) — recommended

### Setup

```bash
# Install toolchain versions (requires mise)
make mise-setup

# Install Python deps, hooks, and the Chromium browser
make setup

# Install frontend deps and build React (optional for backend-only work)
make frontend-build
```

### Run in dev mode

```bash
# Start the backend on a dynamically selected port and Vite on port 5174
make dev

# Or individually
make dev-backend   # application entry point with --reload and dynamic port
make dev-frontend  # vite dev on :5174
```

Open <http://localhost:5174/>. Vite proxies `/api` and `/env.js` to
`http://localhost:8081`, as configured in `frontend/vite.config.ts`. If the
backend selects another port, update both proxy targets before using Vite.

### Run tests

```bash
make test            # pytest (backend, excludes slow)
make frontend-test   # vitest
make test-slow       # slow tests (real subprocess + HF mocks)
```

### Lint + typecheck

```bash
make lint
make typecheck
```

---

## Environment variables

All variables use the `PD_OCR_TRAINER_SPA_` prefix.

<!-- markdownlint-disable MD013 -->

| Variable                               | Default           | Description              |
| -------------------------------------- | ----------------- | ------------------------ |
| `PD_OCR_TRAINER_SPA_PORT`              | `8081`            | Backend port             |
| `PD_OCR_TRAINER_SPA_HOST`              | `127.0.0.1`       | Settings host; CLI overrides it with `--host` |
| `PD_OCR_TRAINER_SPA_ML_TRAINING_DIR`   | `~/ml-training`   | Training dataset root    |
| `PD_OCR_TRAINER_SPA_ML_VALIDATION_DIR` | `~/ml-validation` | Validation dataset root  |
| `PD_OCR_TRAINER_SPA_MATCHED_OCR_DIR`   | `~/matched-ocr`   | Legacy setting; does not select the export root |
| `PD_OCR_TRAINER_SPA_LABELER_EXPORT_ROOT` | unset           | Explicit export root; otherwise discovered through shared paths |
| `PD_OCR_TRAINER_SPA_APP_DATA_ROOT`     | OS-specific       | App data root            |
| `PD_OCR_TRAINER_SPA_SHARED_MODELS_DIR` | `~/shared-models` | Trained model output     |
| `PD_OCR_TRAINER_SPA_ENABLE_HF_PUBLISH` | `false`           | Enable HF publish routes |

<!-- markdownlint-enable MD013 -->

See `src/pdomain_ocr_trainer_spa/settings.py` for the full list.

---

## Architecture

```text
FastAPI process (torch-free)
  ├── /api/*         API routes
  ├── /env.js        Build version + feature flags for SPA
  ├── /healthz       Owned by pdomain-ops mount_routes
  └── /*             React SPA catch-all (serves index.html)

Worker subprocess (torch + DocTR, launched by pdomain-ops LongJobRunner)
  └── pdomain_ocr_trainer_spa.worker.train
        └── pdomain_ocr_training.LocalTrainingRunner (ITrainingRunner)
```

The FastAPI process **never imports torch**. Training is isolated to a worker
subprocess whose lifecycle (start, supervise, cancel) is managed by the
`pdomain-ops` `LongJobRunner`.

---

## Ports

- Backend: dynamically selected from the configured/default port
- Frontend dev: Vite port `5174`, set in `frontend/vite.config.ts`

Set the backend's preferred port with `--port` or
`PD_OCR_TRAINER_SPA_PORT`. Set its host with `--host`; the CLI passes that
value into Settings even when a host environment variable is present.
Change Vite's port and proxy targets in `frontend/vite.config.ts`.

---

## Building a wheel

```bash
make frontend-build   # build SPA → src/pdomain_ocr_trainer_spa/static/
uv build --sdist      # source distribution from the source tree
uv build --wheel      # wheel from the source tree

# Verify SPA bundle is inside the wheel
uv run python -m zipfile -l dist/pdomain_ocr_trainer_spa-*.whl | grep static/index.html
```

## Install from wheel

```bash
uv tool install ./dist/pdomain_ocr_trainer_spa-*.whl
pdomain-ocr-trainer-ui --port 8081
```

## Cut a release locally

This repo has no GitHub Actions workflows.

Cut a release on this machine with `scripts/do-release.sh`. That script calls
`scripts/release-common.sh`.

`scripts/release-common.sh` tags `master` and creates the GitHub Release after
`make ci-slow`, unless `RELEASE_PREFLIGHT` overrides the preflight.

Commit `f5437b31f3d44fddbfc8cf66f44fc3d0e7c6a6b8` removed `.github/workflows`,
including the dated `dep-refresh` workflow.

---

## Diagnostics

```bash
make doctor   # prints Python/Node versions, CUDA/MPS availability, HF token status
```

---

## Switching from the legacy trainer

The new SPA replaces the legacy `pdomain-ocr-training` NiceGUI app. During
cutover the two can run **side by side against the same `ml-training/` tree** —
they read the dataset directories but stage their own mutations, and they are
isolated from each other by two separate namespaces: **ports** and
**environment-variable prefixes**.

### The two apps never collide

<!-- markdownlint-disable MD013 -->

|                | Legacy `pdomain-ocr-training`  | New `pdomain-ocr-trainer-spa`      |
| -------------- | ------------------------------ | ---------------------------------- |
| UI stack       | NiceGUI                        | FastAPI + React/Vite SPA           |
| Entry point    | `pdomain-ocr-training`         | `pdomain-ocr-trainer-ui`           |
| Env-var prefix | `PD_OCR_TRAINER_`              | `PD_OCR_TRAINER_SPA_`              |
| Default port   | `8000`                         | `8081`                             |
| Host env var   | `PD_OCR_TRAINER_HOST`          | `PD_OCR_TRAINER_SPA_HOST`          |
| Port env var   | `PD_OCR_TRAINER_PORT`          | `PD_OCR_TRAINER_SPA_PORT`          |
| App-data dir   | `PD_OCR_TRAINER_APP_DATA_ROOT` | `PD_OCR_TRAINER_SPA_APP_DATA_ROOT` |

<!-- markdownlint-enable MD013 -->

Because the env-var prefixes differ by the `_SPA` segment, a variable set for
one app is **never** read by the other — there is no shared key. A stray
`PD_OCR_TRAINER_PORT=8000` does not move the SPA off `8081`, and vice versa. The
two default ports (`8000` vs `8081`) also differ, so the bare `make dev` /
`pdomain-ocr-trainer-ui` invocations bind distinct sockets with zero
configuration.

### Pointing both at the same `ml-training/`

The dataset trees are **shared on purpose** — both apps should see the same
projects. Point each app at the same directories using its own prefix:

```bash
# Legacy trainer — terminal 1
PD_OCR_TRAINER_ML_TRAINING_DIR=/data/ml-training \
PD_OCR_TRAINER_ML_VALIDATION_DIR=/data/ml-validation \
PD_OCR_TRAINER_SHARED_MODELS_DIR=/data/shared-models \
PD_OCR_TRAINER_PORT=8000 \
  pdomain-ocr-training                       # → http://127.0.0.1:8000

# New SPA — terminal 2
PD_OCR_TRAINER_SPA_ML_TRAINING_DIR=/data/ml-training \
PD_OCR_TRAINER_SPA_ML_VALIDATION_DIR=/data/ml-validation \
PD_OCR_TRAINER_SPA_SHARED_MODELS_DIR=/data/shared-models \
PD_OCR_TRAINER_SPA_PORT=8081 \
  pdomain-ocr-trainer-ui                    # → http://127.0.0.1:8081
```

Verification that they do not collide:

- `curl -sf http://127.0.0.1:8000/` and `curl -sf http://127.0.0.1:8081/` both
  succeed — two live servers, two ports.
- `pdomain-ocr-trainer-spa`'s `/env.js` reports its own version and
  `driverContractVersion`; the legacy NiceGUI app serves no `/env.js`.

### Coexistence caveats

- **App-data directories should stay separate.** Each app keeps its own
  settings/job state under its `*_APP_DATA_ROOT`; leave these at their
  (distinct) defaults, or set them to different paths. They are _not_ a shared
  store.
- **Dataset moves are not transactional across apps.** Both apps stage kanban
  moves locally and apply them to the same `ml-training/` / `ml-validation/`
  trees. Apply moves from one app at a time and rescan the other afterwards to
  pick up the on-disk change.
- **Trained-model outputs are shared.** A run finished in either app writes its
  weights + sidecar under the shared `SHARED_MODELS_DIR`, so the SPA's `/models`
  page lists models trained by the legacy app and vice versa.
