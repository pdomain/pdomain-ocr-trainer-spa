# 14 — Testing strategy

What to test, how, and where. The most critical question for this
SPA is **how to test long-running training without a GPU** — §5
covers that explicitly.

> Required reading: [`02-backend.md`](02-backend.md),
> [`06-training-runs.md`](06-training-runs.md),
> [`10-jobs-and-sse.md`](10-jobs-and-sse.md),
> [`13-driver-contract.md`](13-driver-contract.md).
>
> **Re-spec note (2026-05-21).** The training-test seam moved. The
> SPA no longer owns an `ITrainingRunner` adapter to fake — training
> runs through `pdomain-ocr-training` inside a worker subprocess
> supervised by the `pdomain-ocr-ops` `LongJobRunner` (D-T1, D-T20). The
> CI-safe seam is now a **fake `LongJobRunner`** plus a **stub
> worker script**; there is no `FakeTrainingRunner`.

---

## 1. Test pyramid

| Layer | Tool | What |
|---|---|---|
| Backend unit | `pytest` | Pure functions, `config_build` mapping, `events.py` `@@PDEVENT@@` parsing, sidecar IO, profile.toml round-trip, kanban `apply` diff logic. |
| Backend integration | `pytest` + FastAPI `TestClient` | Every endpoint, every error-code path. Adapters + the `LongJobRunner` wired as fakes (no real subprocess, no real HF). |
| SPA-serving contract | `pytest` | `test_routes_root.py` — the FastAPI catch-all serves the SPA (§6). |
| Backend slow / e2e | `pytest -m slow` | Real `LocalLongJobRunner.submit_with_process` against a stub worker script. Real `huggingface_hub` against a recorded mock. |
| Frontend unit | `vitest` + RTL | Pure components, hooks, lib functions. msw at the network boundary. |
| Frontend e2e | `Playwright` | Full SPA against a real backend with all-fake adapters. |
| Driver contract | `Playwright` | Single spec covering URL + testid invariants from [`13-driver-contract.md`](13-driver-contract.md). |

CI runs **all non-slow layers** on every PR; `slow` is gated to a
nightly job and runnable manually with `make test-slow`.

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
        jobs_db_path=tmp_path / "app-data" / "jobs.db",
        labeler_export_root=None,
        job_runner_kind="fake",
        model_registry_kind="filesystem",
    )

@pytest.fixture
def app(settings):
    return build_app(settings)

@pytest.fixture
def client(app):
    return TestClient(app)

@pytest.fixture
def fake_runner(app) -> FakeLongJobRunner:
    return app.state.app_state.job_runner
```

`FakeLongJobRunner` is the in-test `LongJobRunner`. Instead of
spawning the worker subprocess on `submit` / `submit_with_process`,
it emits a scripted sequence of `pdomain-ocr-ops` `JobEvent`s and
advances `JobStatus.state` through the lifecycle. Tests pin the
script:

```python
fake_runner.script = [
    JobEvent(kind="log",      payload={"stream": "stdout", "line": "Epoch 1/3"}),
    JobEvent(kind="progress", payload={"current": 1, "total": 3, "message": "epoch 1/3"}),
    JobEvent(kind="metric",   payload={"name": "val_cer", "value": 0.10, "step": 1}),
    JobEvent(kind="progress", payload={"current": 2, "total": 3, "message": "epoch 2/3"}),
    JobEvent(kind="metric",   payload={"name": "val_cer", "value": 0.05, "step": 2}),
    JobEvent(kind="state",    payload={"state": "succeeded", "exit_code": 0}),
]
```

(`job_id`, `seq`, `at` are filled in by the fake.) Similar
`FakeDatasetSource`, `FakeModelRegistry`, `FakeStorage`, `FakeAuth`
are available; selection is driven by `Settings.<adapter>_kind="fake"`.

`config_build` and `worker_cmd` are tested as **pure functions** —
no fake needed: assert a given `Run.args` produces a valid
`pdomain_ocr_training.DetectionConfig` / `RecognitionConfig` and the
expected argv.

### 2.2 Endpoint tests

Pattern: `tests/integration/api/test_<router>.py`. Each test starts
from a clean `client`, calls the endpoint, asserts response code +
body shape + on-disk side effects via direct filesystem reads.

```python
def test_create_profile_writes_dirs_and_toml(client, settings):
    r = client.post("/api/profiles", json={"name": "Cló Gaelach", "language": "ga", "typeface": "clogaelach"})
    assert r.status_code == 201
    assert (settings.ml_training_dir / "cló-gaelach" / "profile.toml").exists()
```

### 2.3 SSE testing

`TestClient.stream("GET", "/api/jobs/{id}/events")` plus a small
helper that parses the SSE bytes back into typed `JobEvent` lists.
Driven by the `FakeLongJobRunner` script; the SSE route is exercised
end to end (route → `stream_events` → SSE frame).

### 2.4 Concurrency

Tests for the one-train-job-at-a-time rule (D-T15) and the
cancellation lifecycle drive the `FakeLongJobRunner` (its script can
sleep to simulate work). Cancellation asserts `cancel(job_id)`
flips the job to a `cancelled` terminal `state` event. No real
subprocess, no GPU.

---

## 3. Frontend testing

### 3.1 Vitest + Testing Library

- One test file per component / hook, located adjacent
  (`Component.tsx` ↔ `Component.test.tsx`).
- `userEvent` over `fireEvent`.
- msw `setupServer` in `test/setup.ts`; per-test handlers via
  `server.use(...)`.

### 3.2 Hook tests

Hooks consuming react-query are tested via `renderHook` inside a
`QueryClientProvider`; msw handlers per test simulate backend
responses. The `pdomain-ui` `useLongJob` hook is pdomain-ui's own test
surface — the SPA tests only its *consumption* (e.g.
`useNotificationStream` toasting on a terminal `state` event).

### 3.3 Kanban interaction

The DnD kanban is the `pdomain-ui` `KanbanBoard` component (D-T4) —
dnd-kit internals and keyboard-sensor behaviour are pdomain-ui's test
responsibility. The SPA tests its **composition**: that staged
moves accumulate in client state, that `Apply` POSTs the correct
`ApplyAssignmentRequest` diff, and that `Discard` reverts to
committed truth. These run against msw handlers.

### 3.4 Snapshot tests

Limited to `EvalMetricsTable` (regression-prone formatting) and the
`LossChart` empty state. No component-tree snapshots — they rot.

---

## 4. Playwright (frontend e2e)

### 4.1 Setup

`tests/e2e/conftest.py`:

- Spins up a real FastAPI server with all-fake adapters + the
  `FakeLongJobRunner` via `uvicorn.Config + Server.serve()` in a
  thread.
- Spins up Vite preview (built bundle, not dev) on a free port.
- Yields a Playwright `browser` and the base URL.
- Clean `tmp_path` settings per test.

### 4.2 Scenarios

| Scenario | What it covers |
|---|---|
| `test_create_profile_flow` | New → form → save → row appears |
| `test_kanban_stage_and_apply` | Drag chip → footer pending-count updates → `Apply` → chips commit to column |
| `test_kanban_discard` | Stage moves → `Discard` → board reverts, no request |
| `test_kanban_keyboard` | `?` opens help → `Tab` to first chip → `Space` grab → arrows → `Space` drop → `a` applies |
| `test_run_lifecycle` | Start run → status pending → running → log streams → fake metrics on chart → success → model appears |
| `test_run_cancel` | Start → click Cancel → confirm → status `cancelled` |
| `test_run_reload_resume` | Start → reload page → SSE reconnects, log replays from `Last-Event-ID:` |
| `test_eval_with_glyph_slicing` | Eval form → slice toggle → result page shows slice rows |
| `test_publish_blocked_without_token` | Publish → banner visible → publish form disabled |
| `test_driver_contract` | URL + testid conformance ([`13-driver-contract.md`](13-driver-contract.md) §5) |

---

## 5. Testing without a GPU

Real DocTR training is GPU-bound, large, and unrepeatable in CI.
The test surface decomposes into three layers.

### 5.1 The `LongJobRunner` seam

The CI-safe seam is the `pdomain-ocr-ops` `LongJobRunner` Protocol. CI
never instantiates a runner that spawns the real worker; tests use
`FakeLongJobRunner` (`job_runner_kind="fake"`). This covers:

- Endpoint contracts (`POST /api/runs`, `/api/jobs/*`).
- Job lifecycle and the `JobStatus` projection.
- SSE stream shape.
- Run persistence + crash recovery (`hydrate_from_disk`).
- Failure-mode toasts (script a `failed` terminal `state` event).

### 5.2 Worker emission + event parsing

Two pure-unit surfaces, no GPU:

- **Worker `@@PDEVENT@@` emission** — given a scripted
  `pdomain-ocr-training` `TrainingEvent` sequence, assert `worker/train.py`
  writes the correct `@@PDEVENT@@ {json}` stdout lines. `pdomain-ocr-training`'s
  `LocalTrainingRunner` is itself driven by an injected fake
  training callable (its iterator API makes this trivial — no
  `torch`).
- **`events.py` parsing** — given captured `@@PDEVENT@@` /
  stdout transcripts in `tests/fixtures/training_logs/`, assert
  `training/events.py` maps them to the right SPA `Job` events.

```
tests/fixtures/training_logs/
├── detection_db_resnet50_8epoch.pdevents.txt
├── recognition_crnn_5epoch.pdevents.txt
├── recognition_oom.pdevents.txt          # ends in an error event
├── typeface_classifier_3epoch.pdevents.txt
└── glyph_classifier_3epoch.pdevents.txt
```

Checked-in transcripts captured once and frozen; a manual
`scripts/refresh_log_fixtures.py` re-records them on demand.

> The stdout → `JobEvent` parse on the *runner* side is
> `pdomain-ocr-ops`' responsibility (see the
> [trainer workflow architecture](../docs/architecture/trainer-workflows.md),
> `pdomain-ocr-ops#76`) and is tested there.

### 5.3 Stub worker for slow tests

A `slow` test invokes the real `LocalLongJobRunner.submit_with_
process` against `tests/fixtures/stub_worker.py` — a script that
prints a scripted `@@PDEVENT@@` sequence and exits. This catches
regressions in the subprocess plumbing (env var passing, line
buffering, signal handling, exit-code → state) without CUDA.

```python
# tests/fixtures/stub_worker.py
def main() -> None:
    run_dir = Path(sys.argv[sys.argv.index("--run-dir") + 1])
    args = json.loads((run_dir / "args.json").read_text())
    for i in range(args["epochs"]):
        ev = {"kind": "epoch", "message": f"epoch {i+1}/{args['epochs']}",
              "progress": (i + 1) / args["epochs"], "data": {}}
        print(f"@@PDEVENT@@ {json.dumps(ev)}", flush=True)
        time.sleep(0.05)
    print('@@PDEVENT@@ {"kind":"done","message":"Training completed successfully."}', flush=True)
    sys.exit(0)
```

Real DocTR training is **never** invoked from CI.

---

## 6. SPA-serving contract tests

`pdomain-ocr-trainer-spa` is a FastAPI backend that bundles and serves a
React/Vite SPA (a `StaticFiles` mount + `/{full_path:path}`
catch-all), so per the workspace contract it **must** carry a
`tests/test_routes_root.py` covering:

1. `GET /` → `200` `text/html` — the SPA `index.html` is served.
2. React-Router sub-paths (`/runs/123`, `/profiles/all`) → `200`
   HTML — the catch-all falls through to `index.html`.
3. `/api/*` routes are **not** shadowed by the catch-all (assert a
   known API route still returns its JSON / its real status).
4. `GET /` → `503` when the frontend directory is absent.

These tests **must not skip** when the frontend isn't built. They
use `monkeypatch` + `tmp_path` to create a minimal fake `index.html`
at the `static/` path so they always run in pure-Python mode.
Reference: `pdomain-ocr-simple-gui/tests/test_routes_root.py`.

---

## 7. Coverage targets

- **Backend**: ≥ 90% line coverage on `domain/`, `core/`, `api/`,
  `training/`. Adapters can be lower (real `huggingface_hub` is
  exercised only in slow tests).
- **Frontend**: ≥ 80% on hooks + lib; ≥ 60% on components.

Coverage is reported, not gated; PRs lowering it without
justification are flagged in review.

---

## 8. Test data conventions

- All fixtures under `tests/fixtures/`, one sub-dir per concern
  (`training_logs/`, `kanban/`, `sidecars/`).
- Image fixtures are tiny (1×1 PNG generated at runtime via PIL)
  unless a test needs realistic content.
- No real-world data committed; a real PGDP page, if needed, lives
  under `tests/fixtures/external/` (`.gitignored`) with a `Make`
  target to refresh.

---

## 9. CI matrix

```
matrix:
  python: [3.13]
  node:   [24]
  os:     [ubuntu-22.04]
```

Per-job: `make setup` → `make lint` → `make typecheck` →
`make test` → `make frontend-test` → `make frontend-build` →
`make e2e` → `make build` (wheel; assert SPA bundle included).

A nightly `slow` job runs `make test-slow` — real subprocess
(stub worker) + recorded HF mocks.

---

## 10. Citations

- Test layout: `pdomain-ocr-labeler-spa/specs/14-testing.md`.
- Adapter-fake pattern: `pdomain-prep-for-pgdp/tests/conftest.py`.
- SPA-serving contract test: `pdomain-ocr-simple-gui/tests/test_routes_root.py`.
- `LongJobRunner` Protocol (the fake's target):
  `pdomain-ocr-ops/pdomain_ocr_ops/gpu/protocols.py:27-45`.
