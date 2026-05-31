# Development Guide — pdomain-ocr-trainer-spa

FastAPI + React/Vite SPA that replaces the legacy `pdomain-ocr-training` NiceGUI UI
for OCR model training (detection + recognition + typeface + glyph classifiers).

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

# Install Python + frontend deps, set up pre-commit hooks
make setup

# Build the React frontend (optional for backend-only work)
make frontend-build
```

### Run in dev mode

```bash
# Start backend (port 8081) + Vite dev server (port 5174) concurrently
make dev

# Or individually
make dev-backend   # uvicorn --reload on :8081
make dev-frontend  # vite dev on :5174
```

Open http://localhost:5174/ (Vite proxies /api → :8081).

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

| Variable | Default | Description |
|---|---|---|
| `PD_OCR_TRAINER_SPA_PORT` | `8081` | Backend port |
| `PD_OCR_TRAINER_SPA_HOST` | `127.0.0.1` | Backend host |
| `PD_OCR_TRAINER_SPA_ML_TRAINING_DIR` | `~/ml-training` | Training dataset root |
| `PD_OCR_TRAINER_SPA_ML_VALIDATION_DIR` | `~/ml-validation` | Validation dataset root |
| `PD_OCR_TRAINER_SPA_MATCHED_OCR_DIR` | `~/matched-ocr` | Labeler export root |
| `PD_OCR_TRAINER_SPA_APP_DATA_ROOT` | OS-specific | App data root |
| `PD_OCR_TRAINER_SPA_SHARED_MODELS_DIR` | `~/shared-models` | Trained model output |
| `PD_OCR_TRAINER_SPA_ENABLE_HF_PUBLISH` | `false` | Enable HF publish routes |

See `src/pdomain_ocr_trainer_spa/settings.py` for the full list.

---

## Architecture

```
FastAPI process (torch-free)
  ├── /api/*         API routes
  ├── /env.js        Build version + feature flags for SPA
  ├── /healthz       Owned by pdomain-ocr-ops mount_routes
  └── /*             React SPA catch-all (serves index.html)

Worker subprocess (torch + DocTR, launched by pdomain-ocr-ops LongJobRunner)
  └── pdomain_ocr_trainer_spa.worker.train
        └── pdomain_ocr_training.LocalTrainingRunner (ITrainingRunner)
```

The FastAPI process **never imports torch**. Training is isolated to
a worker subprocess whose lifecycle (start, supervise, cancel) is
managed by the `pdomain-ocr-ops` `LongJobRunner`.

---

## Ports

- Backend: `127.0.0.1:8081` (differs from labeler-spa :8080)
- Frontend dev: `127.0.0.1:5174` (differs from pgdp-prep :5173)

Both ports are configurable via environment variables.

---

## Building a wheel

```bash
make frontend-build   # build SPA → src/pdomain_ocr_trainer_spa/static/
make build            # python -m build → dist/*.whl

# Verify SPA bundle is inside the wheel
python -m zipfile -l dist/pdomain_ocr_trainer_spa-*.whl | grep static/index.html
```

## Install from wheel

```bash
uv tool install ./dist/pdomain_ocr_trainer_spa-*.whl
pdomain-ocr-trainer-ui --port 8081
```

---

## Diagnostics

```bash
make doctor   # prints Python/Node versions, CUDA/MPS availability, HF token status
```

---

## Switching from the legacy trainer

The new SPA replaces the legacy `pdomain-ocr-training` NiceGUI app. During
cutover the two can run **side by side against the same `ml-training/`
tree** — they read the dataset directories but stage their own
mutations, and they are isolated from each other by two separate
namespaces: **ports** and **environment-variable prefixes**.

### The two apps never collide

| | Legacy `pdomain-ocr-training` | New `pdomain-ocr-trainer-spa` |
|---|---|---|
| UI stack | NiceGUI | FastAPI + React/Vite SPA |
| Entry point | `pdomain-ocr-training` | `pdomain-ocr-trainer-ui` |
| Env-var prefix | `PD_OCR_TRAINER_` | `PD_OCR_TRAINER_SPA_` |
| Default port | `8000` | `8081` |
| Host env var | `PD_OCR_TRAINER_HOST` | `PD_OCR_TRAINER_SPA_HOST` |
| Port env var | `PD_OCR_TRAINER_PORT` | `PD_OCR_TRAINER_SPA_PORT` |
| App-data dir | `PD_OCR_TRAINER_APP_DATA_ROOT` | `PD_OCR_TRAINER_SPA_APP_DATA_ROOT` |

Because the env-var prefixes differ by the `_SPA` segment, a variable
set for one app is **never** read by the other — there is no shared
key. A stray `PD_OCR_TRAINER_PORT=8000` does not move the SPA off
`8081`, and vice versa. The two default ports (`8000` vs `8081`) also
differ, so the bare `make dev` / `pdomain-ocr-trainer-ui` invocations bind
distinct sockets with zero configuration.

### Pointing both at the same `ml-training/`

The dataset trees are **shared on purpose** — both apps should see the
same projects. Point each app at the same directories using its own
prefix:

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

- `curl -sf http://127.0.0.1:8000/` and
  `curl -sf http://127.0.0.1:8081/` both succeed — two live servers,
  two ports.
- `pdomain-ocr-trainer-spa`'s `/env.js` reports its own version and
  `driverContractVersion`; the legacy NiceGUI app serves no `/env.js`.

### Coexistence caveats

- **App-data directories should stay separate.** Each app keeps its
  own settings/job state under its `*_APP_DATA_ROOT`; leave these at
  their (distinct) defaults, or set them to different paths. They are
  *not* a shared store.
- **Dataset moves are not transactional across apps.** Both apps stage
  kanban moves locally and apply them to the same `ml-training/` /
  `ml-validation/` trees. Apply moves from one app at a time and
  rescan the other afterwards to pick up the on-disk change.
- **Trained-model outputs are shared.** A run finished in either app
  writes its weights + sidecar under the shared `SHARED_MODELS_DIR`,
  so the SPA's `/models` page lists models trained by the legacy app
  and vice versa.
