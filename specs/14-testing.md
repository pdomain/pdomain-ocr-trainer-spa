# 14 — Testing strategy

What to test, how, and where. The most critical question for this
SPA is **how to test long-running training without a GPU** — §5
covers that explicitly.

> Required reading: [`02-backend.md`](02-backend.md),
> [`06-training-runs.md`](06-training-runs.md),
> [`13-driver-contract.md`](13-driver-contract.md).

---

## 1. Test pyramid

| Layer | Tool | What |
|---|---|---|
| Backend unit | `pytest` | Pure functions, model parsers, sidecar IO, profile.toml round-trip, kanban move logic. |
| Backend integration | `pytest` + FastAPI `TestClient` | Every endpoint, every error code path. Adapters wired with fakes (no real subprocess, no real HF). |
| Backend slow / e2e | `pytest -m slow` | Real `local_subprocess` against a stub `train_*` script. Real `huggingface_hub` against a recorded mock. |
| Frontend unit | `vitest` + RTL | Pure components, hooks, lib functions. msw at the network boundary. |
| Frontend e2e | `Playwright` | Full SPA against a real backend with all-fake adapters. |
| Driver contract | `Playwright` | Single spec covering URL + testid invariants from [`13-driver-contract.md`](13-driver-contract.md). |

CI runs **all of the above** on every PR; `slow` is gated to a
nightly job and can be run manually with `make test-slow`.

---

## 2. Backend testing

### 2.1 Conftest fixtures

```python
# tests/conftest.py

@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        ml_training_dir=tmp_path / "ml-training",
        ml_validation_dir=tmp_path / "ml-validation",
        matched_ocr_dir=tmp_path / "matched-ocr",
        app_data_root=tmp_path / "app-data",
        shared_models_dir=tmp_path / "shared-models",
        runs_dir=tmp_path / "app-data" / "runs",
        labeler_export_root=None,
        training_runner_kind="fake",
        model_registry_kind="filesystem",
    )

@pytest.fixture
def app(settings):
    return build_app(settings)

@pytest.fixture
def client(app):
    return TestClient(app)

@pytest.fixture
def fake_runner(app) -> FakeTrainingRunner:
    return app.state.app_state.training_runner
```

`FakeTrainingRunner` is the in-test impl of `ITrainingRunner`. It
emits a scripted sequence of `JobEvent`s on `start()` rather than
spawning a subprocess. Tests can pin the script:

```python
fake_runner.script = [
    JobEvent.log(stream="stdout", line="Epoch 1/3"),
    JobEvent.progress(current=1, total=3),
    JobEvent.metric(name="val_cer", value=0.10, step=1),
    JobEvent.log(stream="stdout", line="Epoch 2/3"),
    JobEvent.progress(current=2, total=3),
    JobEvent.metric(name="val_cer", value=0.05, step=2),
    JobEvent.complete(exit_code=0),
]
```

Similar `FakeDatasetSource`, `FakeModelRegistry`, `FakeStorage`,
`FakeAuth` available; selection driven by
`Settings.<adapter>_kind="fake"`.

### 2.2 Endpoint tests

Pattern: `tests/integration/api/test_<router>.py`. Each test starts
from a clean `client`, calls the endpoint, asserts response code +
body shape + side effects on disk via direct filesystem reads.

```python
def test_create_profile_writes_dirs_and_toml(client, settings):
    r = client.post("/api/profiles", json={"name": "Cló Gaelach", "language": "ga", "typeface": "clogaelach"})
    assert r.status_code == 201
    assert (settings.ml_training_dir / "cló-gaelach" / "profile.toml").exists()
```

### 2.3 SSE testing

`TestClient.stream("GET", "/api/jobs/{id}/events")` plus a small
helper that parses the SSE bytes back into typed `JobEvent` lists.
Driven by the `FakeTrainingRunner` scripts.

### 2.4 Concurrency

Tests for the per-`(profile, task)` single-running rule and
for the cancellation grace-period semantics use real threads
against the `FakeTrainingRunner` (the runner sleeps inside its
script to simulate work). No subprocess.

---

## 3. Frontend testing

### 3.1 Vitest + Testing Library

- One test file per component / hook; located adjacent
  (`Component.tsx` ↔ `Component.test.tsx`).
- `userEvent` over `fireEvent`. No raw DOM events except for
  testing dnd-kit's keyboard sensor.
- msw `setupServer` in `test/setup.ts`; per-test handlers via
  `server.use(...)`.

### 3.2 Hook tests

Hooks that consume react-query are tested via `renderHook` inside
a `QueryClientProvider`. msw handlers per test simulate backend
responses. No mocking of react-query directly.

### 3.3 Drag-and-drop

dnd-kit ships testing utilities. The kanban tests use the
`KeyboardSensor` path (deterministic) instead of mouse events.
Tests that need pointer-style DnD use `installPointerEvent()` and
synthesise events.

### 3.4 Snapshot tests

Limited to the `EvalMetricsTable` (regression-prone formatting)
and `LossChart` empty-state. No component-tree snapshots — they
rot fast.

---

## 4. Playwright (frontend e2e)

### 4.1 Setup

`tests/e2e/conftest.py`:

- Spins up a real FastAPI server with all-fake adapters via
  `uvicorn.Config + Server.serve()` in a thread.
- Spins up Vite preview (built bundle, not dev) on a free port.
- Yields a Playwright `browser` and the base URL.
- Clean `tmp_path` settings per test.

### 4.2 Scenarios

| Scenario | What it covers |
|---|---|
| `test_create_profile_flow` | New → form → save → row appears |
| `test_kanban_move_and_save` | Drag chip → status footer updates → Copy to Datasets → chips move column |
| `test_kanban_keyboard` | `?` opens help → `Tab` to first chip → `Space` grab → arrows → `Space` drop |
| `test_run_lifecycle` | Start run → status pending → running → log streams → fake metrics on chart → success → model appears |
| `test_run_cancel` | Start → click Cancel → confirm → status `cancelled` |
| `test_run_reload_resume` | Start → reload page → log resumes from buffered events |
| `test_eval_with_glyph_slicing` | Eval form → slice toggle → result page shows slice rows |
| `test_publish_blocked_without_token` | Publish → banner visible → publish form disabled |
| `test_driver_contract` | URL + testid conformance ([`13-driver-contract.md`](13-driver-contract.md) §5) |

---

## 5. Testing without a GPU

The hardest part. Real DocTR training is GPU-bound, large, and
unrepeatable in CI. The test surface decomposes into three layers:

### 5.1 Adapter boundary

`ITrainingRunner` is the seam. CI never instantiates
`local_subprocess`; tests use `FakeTrainingRunner`. This covers:

- Endpoint contracts.
- Job lifecycle.
- SSE stream shape.
- Run persistence + crash recovery.
- Failure-mode toasts.

### 5.2 Subprocess parser tests

`adapters/training/parsers.py` is the regex set per task. Unit
tests feed it sample stdout transcripts captured from real
training runs (kept in `tests/fixtures/training_logs/`) and
assert progress + metric extraction is correct. No GPU needed.

```
tests/fixtures/training_logs/
├── detection_db_resnet50_8epoch.txt
├── recognition_crnn_5epoch.txt
├── recognition_oom.txt              # truncated trace
├── typeface_classifier_3epoch.txt
└── glyph_classifier_3epoch.txt
```

These fixtures are checked-in transcripts — captured once from a
real training run and frozen. Refresh strategy: a manual script
under `scripts/refresh_log_fixtures.py` re-runs short trainings
and overwrites the fixtures on demand.

### 5.3 Stub trainer for slow tests

A `slow` test invokes the real `local_subprocess` runner against
`tests/fixtures/stub_trainer.py` — a script that prints a scripted
progress sequence and exits. This catches regressions in the
subprocess plumbing (env var passing, line buffering, signal
handling) without needing CUDA.

```python
# tests/fixtures/stub_trainer.py
def main():
    args = json.loads(open(sys.argv[2]).read())
    for i in range(args["epochs"]):
        print(f"Epoch {i+1}/{args['epochs']}", flush=True)
        time.sleep(0.05)
        print(f"val_cer: {0.1 * (1 - i / args['epochs']):.4f}", flush=True)
    sys.exit(0)
```

Real DocTR training is **never** invoked from CI.

---

## 6. Coverage targets

- **Backend**: ≥ 90% line coverage on `domain/`, `core/`, `api/`.
  Adapters can be lower because the `local_subprocess` and
  `huggingface_hub` impls are exercised only in slow tests.
- **Frontend**: ≥ 80% on hooks + lib; ≥ 60% on components
  (snapshot-heavy components are excluded from the coverage
  metric).

Coverage is reported, not gated. PRs that lower it without
justification are flagged in review.

---

## 7. Test data conventions

- All fixtures under `tests/fixtures/`.
- One sub-dir per concern (`training_logs/`, `kanban/`, `sidecars/`).
- Image fixtures are tiny (1×1 PNG generated at runtime via PIL)
  unless the test specifically needs realistic content.
- No real-world data committed; if a test needs a real PGDP page,
  it lives under `tests/fixtures/external/` and is `.gitignored`,
  with a `Make` target to refresh.

---

## 8. CI matrix

```
matrix:
  python: [3.13]
  node:   [24]
  os:     [ubuntu-22.04]
```

Per-job:

1. `make setup`
2. `make lint`
3. `make typecheck`
4. `make test`
5. `make frontend-test`
6. `make frontend-build`
7. `make e2e` (Playwright)
8. `make build` (wheel; assert SPA bundle is included)

A nightly `slow` job runs `make test-slow` — exercises real
subprocess + recorded HF mocks.

---

## 9. Citations

- Test layout: `pd-ocr-labeler-spa/specs/14-testing.md`.
- Adapter-fake pattern: `pd-prep-for-pgdp/tests/conftest.py`.
- Stub-subprocess pattern: `pd-ocr-cli/tests/fixtures/stub_*`.
