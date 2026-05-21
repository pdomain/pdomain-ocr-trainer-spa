# Development Guide — pd-ocr-trainer-spa

FastAPI + React/Vite SPA that replaces the legacy `pd-ocr-trainer` NiceGUI UI
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

See `src/pd_ocr_trainer_spa/settings.py` for the full list.

---

## Architecture

```
FastAPI process (torch-free)
  ├── /api/*         API routes
  ├── /env.js        Build version + feature flags for SPA
  ├── /healthz       Owned by pd-ocr-ops mount_routes
  └── /*             React SPA catch-all (serves index.html)

Worker subprocess (torch + DocTR, launched by pd-ocr-ops LongJobRunner)
  └── pd_ocr_trainer_spa.worker.train
        └── pd_ocr_training.LocalTrainingRunner (ITrainingRunner)
```

The FastAPI process **never imports torch**. Training is isolated to
a worker subprocess whose lifecycle (start, supervise, cancel) is
managed by the `pd-ocr-ops` `LongJobRunner`.

---

## Ports

- Backend: `127.0.0.1:8081` (differs from labeler-spa :8080)
- Frontend dev: `127.0.0.1:5174` (differs from pgdp-prep :5173)

Both ports are configurable via environment variables.

---

## Building a wheel

```bash
make frontend-build   # build SPA → src/pd_ocr_trainer_spa/static/
make build            # python -m build → dist/*.whl

# Verify SPA bundle is inside the wheel
python -m zipfile -l dist/pd_ocr_trainer_spa-*.whl | grep static/index.html
```

## Install from wheel

```bash
uv tool install ./dist/pd_ocr_trainer_spa-*.whl
pd-ocr-trainer-ui --port 8081
```

---

## Diagnostics

```bash
make doctor   # prints Python/Node versions, CUDA/MPS availability, HF token status
```
