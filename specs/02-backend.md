# 02 — Backend

FastAPI module layout, the `build_app(settings)` factory, every
adapter Protocol, the training-worker subprocess boundary, and the
full route map.

> Required reading: [`00-overview.md`](00-overview.md),
> [`01-data-models.md`](01-data-models.md). For long jobs see
> [`10-jobs-and-sse.md`](10-jobs-and-sse.md).
>
> **Re-spec note (2026-05-21).** This spec was rewritten onto the
> `pdomain-ui` + `pdomain-ocr-ops` + `pdomain-ocr-training` stack. Decisions D-T1,
> D-T9, D-T10, D-T19–D-T22 in [`17-decisions.md`](17-decisions.md)
> are authoritative; where this spec and a decision disagree, the
> decision wins. The original SPA-local `core/job_runner.py` and the
> SPA-local `ITrainingRunner` Protocol are superseded.

---

## 1. Module layout

```
src/pdomain_ocr_trainer_spa/
├── __init__.py
├── __main__.py                # uvicorn entry; reads env, calls build_app, runs server
├── bootstrap.py               # build_app(settings) factory
├── settings.py                # Settings (pydantic-settings)
├── core/
│   ├── app_state.py           # AppState dataclass + get_app_state dep
│   ├── notifications.py       # ring buffer + SSE bus (see 11-notifications.md)
│   ├── paths.py               # OS-aware roots (verbatim port of dataset_store path logic)
│   └── errors.py              # ErrorCode + HTTPException helpers
├── adapters/
│   ├── storage/__init__.py    # IStorage Protocol
│   ├── storage/filesystem.py  # default impl
│   ├── storage/s3.py          # NotImplementedYet
│   ├── auth/__init__.py       # IAuth Protocol + none
│   ├── dataset_sources/__init__.py
│   ├── dataset_sources/local.py
│   ├── dataset_sources/huggingface.py   # NotImplementedYet (D-T2)
│   ├── model_registry/__init__.py
│   ├── model_registry/filesystem.py
│   └── model_registry/huggingface_hub.py
├── training/
│   ├── config_build.py        # Run.args → pdomain_ocr_training DetectionConfig / RecognitionConfig
│   ├── worker_cmd.py           # build_worker_cmd(run, settings) → list[str]
│   └── events.py               # TrainingEvent (worker stdout) ↔ Job event mapping
├── worker/
│   ├── __init__.py
│   └── train.py                # `python -m pdomain_ocr_trainer_spa.worker.train` — the training subprocess
├── domain/
│   ├── profiles.py            # Profile, ProfileCounts, profile.toml IO
│   ├── datasets.py            # DatasetView assembly, kanban move logic
│   ├── runs.py                # Run model + on-disk persistence
│   ├── models.py              # TrainedModel discovery, sidecar IO
│   └── publish.py             # HF publish orchestration
├── api/
│   ├── healthz.py             # (delegated — see §3; pdomain-ocr-ops owns /healthz)
│   ├── env_js.py              # GET /env.js (build version, feature flags)
│   ├── profiles.py            # /api/profiles/...
│   ├── datasets.py            # /api/profiles/{p}/datasets/...
│   ├── runs.py                # /api/runs/...
│   ├── jobs.py                # /api/jobs/{id} + /api/jobs/{id}/events SSE (wraps LongJobRunner)
│   ├── eval.py                # /api/eval/...
│   ├── models.py              # /api/models/...
│   ├── sources.py             # /api/sources/...
│   ├── publish.py             # /api/publish/...
│   └── settings.py            # /api/settings (read-only OCR config / vocabs)
├── middleware/
│   ├── request_id.py
│   └── error_handler.py
├── static/                    # SPA build output, populated by build_hooks/spa_check.py
│   └── .gitkeep
└── _version.py                # hatch-vcs writes this on build
```

**Two import boundaries matter (D-T1, D-T9):**

- The **long-lived FastAPI process** imports `pdomain-ocr-ops` (suite +
  `LongJobRunner`) and the **`torch`-free** half of `pdomain-ocr-training`
  — only the typed config models `DetectionConfig` /
  `RecognitionConfig` / `TrainingEvent` and the `ITrainingRunner`
  Protocol. It never imports `torch`, DocTR, or
  `pdomain_ocr_training.LocalTrainingRunner`.
- The **`worker/train.py` subprocess** is the only place that imports
  `pdomain_ocr_training.LocalTrainingRunner` (and therefore `torch` /
  DocTR). It is launched, supervised, and killed by the `pdomain-ocr-ops`
  `LongJobRunner`; the web process stays `torch`-free.

`pdomain_ocr_training.datasets` (`ExportManager`) has **import-time
filesystem side effects** and still carries `PD_OCR_TRAINER_*` env
prefixes — see §4.4. Import it lazily, inside the worker or inside a
function, never at web-process module scope.

---

## 2. `Settings` (env-driven)

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PD_OCR_TRAINER_SPA_", env_file=None)

    # Paths
    ml_training_dir: Path
    ml_validation_dir: Path
    matched_ocr_dir: Path
    app_data_root: Path                  # OS-aware; overridable
    shared_models_dir: Path
    runs_dir: Path                        # = app_data_root / "runs"
    labeler_export_root: Path | None      # default: matched-ocr / labeler convention

    # Adapters
    storage_kind: Literal["filesystem", "s3"] = "filesystem"
    auth_kind: Literal["none"] = "none"
    job_runner_kind: Literal["local", "modal", "shared_container"] = "local"
    model_registry_kind: Literal["filesystem", "huggingface_hub"] = "filesystem"

    # Jobs / GPU
    jobs_db_path: Path | None = None      # default: pdomain-ocr-ops suite paths.jobs_db_path()

    # HF
    hf_token_path: Path | None = None     # default: ~/.huggingface/token
    hf_default_owner: str | None = None   # e.g. "ntw8532"
    hf_cache_dir: Path | None = None      # maps to HF_HOME

    # Server
    host: str = "127.0.0.1"
    port: int = 8081                       # different default from labeler-spa (8080) — D-T8
    cors_allow_origins: list[str] = ["http://localhost:5174"]   # vite dev — D-T8
    log_level: str = "INFO"

    # Feature flags
    enable_typeface_training: bool = True
    enable_glyph_training: bool = True
    enable_hf_publish: bool = False        # gated until M-HF-Publish ships (D-T2)

    @model_validator(mode="after")
    def _resolve_paths(self) -> "Settings":
        # absolute, expanduser, mkdir-as-needed for the writeable ones
        ...
```

Defaults match the legacy trainer's `dataset_store.py:18-54` — same
OS-aware fallbacks, same env var precedence. Prefix is
`PD_OCR_TRAINER_SPA_` (D-T7) so the new binary coexists with the
legacy trainer. `job_runner_kind` selects which `pdomain-ocr-ops`
`LongJobRunner` implementation backs long jobs (`local` is the only
one wired for core parity; `modal` / `shared_container` are
`pdomain-ocr-ops` concerns, not SPA adapters). ([Q7](../OPEN_QUESTIONS.md))

---

## 3. `build_app(settings)` factory

```python
def build_app(settings: Settings) -> FastAPI:
    app = FastAPI(
        title="pdomain-ocr-trainer-spa",
        version=_version.__version__,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_allow_origins, ...)

    storage = _build_storage(settings)
    auth = _build_auth(settings)
    dataset_sources = _build_dataset_sources(settings)
    model_registry = _build_model_registry(settings)
    job_runner = _build_job_runner(settings)        # pdomain-ocr-ops LongJobRunner (D-T20)

    state = AppState(
        settings=settings,
        storage=storage, auth=auth,
        dataset_sources=dataset_sources, model_registry=model_registry,
        job_runner=job_runner,
    )
    state.hydrate_from_disk()                       # reconciles running-at-boot runs — D-T3
    app.state.app_state = state

    # pdomain-ocr-ops suite plumbing: registry, UI-prefs, sibling-spawn, /healthz (D-T21)
    mount_routes(app, _suite_adapters(settings))

    app.include_router(env_js.router)
    app.include_router(profiles.router, prefix="/api/profiles", tags=["profiles"])
    app.include_router(datasets.router, prefix="/api/profiles", tags=["datasets"])
    app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
    app.include_router(eval.router, prefix="/api/eval", tags=["eval"])
    app.include_router(models.router, prefix="/api/models", tags=["models"])
    app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
    app.include_router(publish.router, prefix="/api/publish", tags=["publish"])
    app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])

    app.add_exception_handler(AppError, app_error_handler)
    app.mount("/", StaticFiles(directory=_static_dir(), html=True), name="spa")

    return app
```

`__main__.py` reads env vars, constructs `Settings()`, and runs
`uvicorn.run(build_app(settings), host=..., port=...)`.

`mount_routes` is `pdomain_ocr_ops.suite.mount_routes` (D-T21). It owns
`/healthz`, `/api/suite/installed`, `/api/suite/launch`,
`/api/suite/prefs*`, and `/api/icons/*`. The SPA does **not** define
`/healthz` or any `/api/suite/*` route itself; `api/healthz.py` is a
thin shim only if a SPA-specific readiness probe is later needed.
`pdomain-ocr-ops` `mount_routes` deliberately exposes **no** job/SSE
routes, so the SPA owns `/api/jobs/*` itself (§5.5).

`_build_job_runner` returns a `pdomain-ocr-ops` `LongJobRunner`. For
`job_runner_kind="local"` it is `LocalLongJobRunner(db_path=
settings.jobs_db_path or <suite default>)`.

---

## 4. Adapter Protocols

### 4.1 `IStorage`

Verbatim port from labeler-spa. Profile-scoped key namespace
(`profile_root_for(profile) / key`). Path-traversal guard.

```python
class IStorage(Protocol):
    def write_bytes(self, scope_root: Path, key: str, data: bytes) -> None: ...
    def read_bytes(self, scope_root: Path, key: str) -> bytes: ...
    def exists(self, scope_root: Path, key: str) -> bool: ...
    def delete(self, scope_root: Path, key: str) -> None: ...
    def list(self, scope_root: Path, prefix: str) -> Iterator[str]: ...
```

### 4.2 `IAuth`

```python
class IAuth(Protocol):
    def current_user(self, request: Request) -> AuthedUser | None: ...
```

The `none` impl returns a fixed `AuthedUser(id="local", roles=["admin"])`.

### 4.3 Training — `ITrainingRunner` is imported, not defined here

The SPA does **not** declare its own training Protocol. Training is
owned by `pdomain-ocr-training`:

- `pdomain_ocr_training.ITrainingRunner` — `@runtime_checkable` Protocol
  with two **generator** methods:

  ```python
  def train_detection(self, profile: str, config: DetectionConfig) -> Iterator[TrainingEvent]
  def train_recognition(self, profile: str, config: RecognitionConfig) -> Iterator[TrainingEvent]
  ```

  `profile` is the run identifier (used as the checkpoint name when
  `config.name` is `None`). The iterator is lazy, never raises, and
  its final event is `kind="done"` or `kind="error"`.

- `DetectionConfig` / `RecognitionConfig` — `torch`-free pydantic
  models (full field lists in
  [`04-profiles-and-config.md`](04-profiles-and-config.md) §3.2).
  `RecognitionConfig.vocab` is a plain `str` — a DocTR vocab name or
  the literal `"CUSTOM:<chars>"`; no validation in the config layer.

- `TrainingEvent` — pydantic model:
  `kind: Literal["log","epoch","metric","done","error"]`,
  `message: str`, `progress: float | None` (normalized `[0,1]`, set
  on `epoch` events), `data: dict | None`.

- `pdomain_ocr_training.LocalTrainingRunner` — the concrete
  `ITrainingRunner`. It runs the blocking DocTR training in an
  **in-process daemon thread** and bridges its callback into the
  iterator. It has **no cancellation hook**: abandoning the iterator
  leaves the thread (and the GPU) held until training finishes
  naturally. This is the decisive reason training runs in a worker
  subprocess (D-T1) — the subprocess *is* the cancellation boundary.

**SPA `training/` package** — the SPA's only training code is glue,
no `torch`:

- `config_build.py` — `build_detection_config(run) -> DetectionConfig`
  and `build_recognition_config(run) -> RecognitionConfig`, mapping a
  persisted `Run.args` dict onto the typed config. For recognition it
  resolves `vocab_library` + `custom_characters` into the final
  `vocab` string (`"CUSTOM:<chars>"` or a named vocab) before the run
  is even submitted.
- `worker_cmd.py` — `build_worker_cmd(run, settings) -> list[str]`,
  the argv handed to the `LongJobRunner` (see §5).
- `events.py` — parses the worker's stdout event protocol (§5.2) back
  into the SPA `Job` event shape consumed by the SSE route.

`modal` / `shared_container` execution targets are `pdomain-ocr-ops`
`LongJobRunner` implementations, not SPA adapters; selecting one is
`Settings.job_runner_kind`.

### 4.4 `IDatasetSource`

```python
class IDatasetSource(Protocol):
    name: str           # "local" | "huggingface"
    def list(self, profile: str, task: TaskEnum, split: SplitEnum) -> Iterator[DatasetPageRef | DatasetCropRef]: ...
    def fetch_to_local(self, profile: str, task: TaskEnum, split: SplitEnum) -> Path: ...
    """Materialize the source data into a local DocTR-compatible directory and return its path."""
```

`local` impl wraps `pdomain_ocr_training.datasets.ExportManager` — the
dataset directory layout is:

```
<ml_training_dir>/<profile>/<task>/images/*.{png,jpg}
<ml_training_dir>/<profile>/<task>/labels.json
<ml_validation_dir>/<profile>/<task>/...   (same shape)
```

`<task>` ∈ `("detection", "recognition")`; `<profile>` default
`"all"` (legacy `"base-ocr"` auto-mapped). A task folder counts as a
dataset only if `<task>/labels.json` exists. `labels.json` is a flat
`{image_filename: label_value}` JSON object; `ExportManager` treats
the value shape as opaque.

⚠️ `ExportManager` performs `mkdir` at **import time** and reads the
legacy `PD_OCR_TRAINER_ML_TRAINING_DIR` / `..._ML_VALIDATION_DIR` env
vars (not the SPA prefix). The `local` adapter must set those env
vars from `Settings` before importing the module, and import it
lazily. ([Q7](../OPEN_QUESTIONS.md))

`huggingface` impl is **deferred — post-core-parity** (D-T2); the
file is `NotImplementedYet`.

### 4.5 `IModelRegistry`

```python
class IModelRegistry(Protocol):
    def list(self) -> list[TrainedModel]: ...
    def get(self, name: str) -> TrainedModel | None: ...
    def write_artefacts(self, run: Run, paths: ModelPaths, sidecar: ModelSidecar) -> TrainedModel: ...
    def publish(self, model: TrainedModel, repo: str, on_event: Callable[[JobEvent], None]) -> ModelPublication: ...
```

`filesystem` impl manages `<shared-models>/<profile>/<task>/...`.
`huggingface_hub` impl wraps `HfApi.upload_large_folder`; gated by
`Settings.enable_hf_publish` (D-T2). ([Q8](../OPEN_QUESTIONS.md))

---

## 5. Training-worker subprocess

A training run executes as a worker subprocess whose lifecycle is
owned by the `pdomain-ocr-ops` `LongJobRunner` (D-T1, D-T20). The full
run lifecycle is [`06-training-runs.md`](06-training-runs.md); the
job/SSE transport is [`10-jobs-and-sse.md`](10-jobs-and-sse.md).
This section fixes the **backend ↔ worker contract**.

### 5.1 Submission

`POST /api/runs` (§5.4) writes `runs/<id>/{manifest,args}.json`,
builds the worker argv, and submits it:

```python
cmd = build_worker_cmd(run, settings)
#   → [sys.executable, "-m", "pdomain_ocr_trainer_spa.worker.train",
#      "--run-dir", str(settings.runs_dir / run.id)]
job_id = await job_runner.submit_with_process(
    kind=f"train.{run.task}",          # "train.detection" | "train.recognition" | ...
    spec={"run_id": run.id},
    cmd=cmd,
)
```

`LocalLongJobRunner.submit_with_process` spawns the subprocess,
captures stdout/stderr, sets job state `running`, and supervises it:
exit 0 → `succeeded`; non-zero → `failed` with `error` = last stderr
line. `cancel(job_id)` is SIGTERM + grace + SIGKILL on the
subprocess — the hard cancellation `LocalTrainingRunner` cannot
provide in-process.

### 5.2 Worker stdout event protocol

`worker/train.py`:

1. Reads `runs/<id>/args.json` + `manifest.json`.
2. Builds the typed config via `training/config_build.py`.
3. Sets `HF_HOME`, `CUDA_VISIBLE_DEVICES`, and
   `PD_OCR_TRAINER_*` dataset-dir env vars from the manifest.
4. Instantiates `pdomain_ocr_training.LocalTrainingRunner` and iterates
   `train_detection` / `train_recognition` to completion (it **must**
   drain the iterator fully — abandoning it strands the GPU).
5. For every `TrainingEvent`, writes **one line** to stdout:

   ```
   @@PDEVENT@@ {"kind":"epoch","message":"...","progress":0.03,"data":{...}}
   ```

   and the human-readable `message` to `runs/<id>/stdout.log`. Raw
   subprocess stderr goes to `runs/<id>/stderr.log`.
6. Exits `0` after a `done` event, non-zero after `error` (the
   `error` event's message is the final stderr line, so the
   `LongJobRunner` surfaces it on the `JobStatus`).

The `@@PDEVENT@@`-prefixed JSON line is the **structured progress
channel**. `pdomain-ocr-ops` `LongJobRunner` parses these lines from the
supervised subprocess stdout into `JobEvent`s exposed by
`stream_events(job_id)`; the `TrainingEvent.kind` values map to
`JobEvent.kind` as: `epoch`/`metric` → `progress`/`metric`,
`log` → `log`, `done`/`error` → `state`.

> **Cross-repo prerequisite.** As of 2026-05-21 `LocalLongJobRunner`
> supervises a subprocess but does **not yet** parse its stdout into
> `job_events` (`_append_event` is private; no public emit/parse
> API). This re-spec therefore depends on a `pdomain-ocr-ops` enhancement:
> a documented subprocess-stdout → `JobEvent` parser keyed on the
> `@@PDEVENT@@` prefix. Until that lands, `stream_events()` yields
> only terminal state and the SPA progress bar/log stream are blank
> mid-run. Tracked as a `pdomain-ocr-ops` feature request — see
> [Q27](../OPEN_QUESTIONS.md). The `@@PDEVENT@@` line format above is
> the proposed contract for that parser.

### 5.3 Crash recovery

If the FastAPI process dies mid-run, the worker subprocess is an
orphan and the `LongJobRunner` job registry (SQLite) survives but its
in-memory process handle does not. `AppState.hydrate_from_disk`
reconciles: any `Run` left in `running` with no live job is marked
`failed`, `exit_code = -1`, and a synthetic line appended to
`stderr.log` (D-T3). On-disk `runs/<id>/progress.jsonl` preserves the
chart series.

---

## 6. Full route map

> Conventions: all paths under `/api`. JSON in/out except where SSE
> is noted. `404` if any path-segment entity is unknown. `409` for
> conflicting concurrent state. `422` for Pydantic validation. `500`
> only on truly unexpected internal errors. All errors are
> `ErrorEnvelope` (see §7).

### 6.1 Health / build info

| Method | Path | Body | Returns | Notes |
|---|---|---|---|---|
| GET | `/healthz` | — | `{"status":"ok"}` | Owned by `pdomain-ocr-ops` `mount_routes` (D-T21). |
| GET | `/env.js` | — | JS file | Inlines `__APP_ENV__ = {version, features}` for the SPA. |

### 6.2 Profiles (`api/profiles.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/profiles` | — | `list[Profile]` |
| GET | `/api/profiles/{name}` | — | `Profile` |
| POST | `/api/profiles` | `CreateProfileRequest{name, display_name?, language?, typeface?}` | `Profile` (201) |
| PATCH | `/api/profiles/{name}` | `UpdateProfileRequest{display_name?, language?, typeface?}` | `Profile` |
| DELETE | `/api/profiles/{name}` | — | `204`. Refuses if any data lives under the profile (`409 profile.has_data`). |
| POST | `/api/profiles/migrate-legacy` | — | `{moved_paths: [...]}` |

`POST /api/profiles/migrate-legacy` triggers
`migrate_legacy_dataset_layout()`. Legacy `base-ocr` → `all` rename
happens implicitly on first `/api/profiles` GET; explicit endpoint
exists for tests.

### 6.3 Datasets (`api/datasets.py`)

All under `/api/profiles/{profile}` prefix. Kanban reassignment is
staged client-side and committed atomically (D-T23):

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/profiles/{profile}/datasets/{task}/kanban` | — | `KanbanView` (3 columns × N rows) |
| POST | `/api/profiles/{profile}/datasets/{task}/apply` | `ApplyAssignmentRequest{assignments: [{page_key, target_split}]}` | `KanbanView` |
| POST | `/api/profiles/{profile}/datasets/{task}/include-toggles` | `{include_detection: bool, include_recognition: bool}` | `KanbanView` |
| POST | `/api/profiles/{profile}/datasets/{task}/scan` | — | `KanbanView` (forces re-scan of export root + on-disk) |

`apply` commits the full staged target-split assignment in one batch
(D-T23); there is no per-drag endpoint. The kanban semantics live in
[`05-dataset-kanban.md`](05-dataset-kanban.md).

### 6.4 Runs (`api/runs.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/runs` | — | `list[Run]` (paginated; default 100) |
| GET | `/api/runs/{run_id}` | — | `Run` |
| POST | `/api/runs` | `CreateRunRequest{profile, task, kind, args, sources?, ...}` | `Run` (202; includes `job_id`) |
| POST | `/api/runs/{run_id}/cancel` | — | `Run` (status → `cancelled` once subprocess dies) |
| GET | `/api/runs/{run_id}/log` | `?stream=stdout|stderr&from_byte=N` | `text/plain` (tail) |
| GET | `/api/runs/{run_id}/progress` | — | `application/x-ndjson` (on-disk `progress.jsonl`) |
| DELETE | `/api/runs/{run_id}` | — | `204`. Refuses if running. |

`POST /api/runs` submits the training worker via
`LongJobRunner.submit_with_process` (§5.1).
`POST /api/runs/{run_id}/cancel` is a thin wrapper that finds the
run's active job and calls `LongJobRunner.cancel`.

### 6.5 Jobs (`api/jobs.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/jobs/{job_id}` | — | `Job` (projected from `LongJobRunner.status`) |
| GET | `/api/jobs/{job_id}/events` | — | `text/event-stream` (SSE) |
| POST | `/api/jobs/{job_id}/cancel` | — | `202 Job` |
| GET | `/api/jobs/active-count` | — | `{count, by_kind}` |

`pdomain-ocr-ops` `mount_routes` exposes **no** job routes, so the SPA
defines these itself, wrapping the `LongJobRunner`:

- `GET /api/jobs/{job_id}` projects `LongJobRunner.status(job_id)`
  (`JobStatus{job_id, kind, state, progress, started_at,
  finished_at, error}`) onto the SPA `Job` model.
- `GET /api/jobs/{job_id}/events` is a `StreamingResponse` that
  `async for`s over `LongJobRunner.stream_events(job_id)` and
  re-emits each `JobEvent` as a `text/event-stream` frame.
- `UnknownJobError` from the runner → `404 job.unknown`.

SSE event shapes and reconnect behaviour: see
[`10-jobs-and-sse.md`](10-jobs-and-sse.md).

### 6.6 Eval (`api/eval.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/eval` | `EvalRequest{profile, task, model_name?, val_source?}` | `Run` (kind=`eval`) |
| GET | `/api/eval/{run_id}/result` | — | `EvalResult` (CER/WER overall + sliced; see [`07-evaluation-and-metrics.md`](07-evaluation-and-metrics.md)) |

### 6.7 Models (`api/models.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/models` | `?profile=&task=` | `list[TrainedModel]` |
| GET | `/api/models/{name}` | — | `TrainedModel` |
| GET | `/api/models/{name}/sidecar` | — | `ModelSidecar` |
| POST | `/api/models/{name}/rename` | `{new_name}` | `TrainedModel` |
| DELETE | `/api/models/{name}` | — | `204`. |

### 6.8 Sources (`api/sources.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/sources` | — | `list[DatasetSourceInfo]` |
| GET | `/api/sources/{name}/profiles/{profile}/datasets/{task}/preview` | — | first ~50 rows for kanban preview when `huggingface` source is configured |

### 6.9 Publish (`api/publish.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/publish/dataset` | `PublishDatasetRequest{profile, task, repo, visibility}` | `Run` (kind=`publish-dataset`) |
| POST | `/api/publish/model` | `PublishModelRequest{model_name, repo, visibility}` | `Run` (kind=`publish-model`) |

Both gated by `Settings.enable_hf_publish`. Returns `403
publish.disabled` when off.

### 6.10 Settings (`api/settings.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/settings` | — | `PublicSettings` (paths, feature flags, vocabs cache info) |
| GET | `/api/settings/vocabs` | — | `dict[str, str]` (DocTR `VOCABS` map) |

The vocab list is resolved inside the worker / a lazy helper, never
by importing `torch`/DocTR into the web process.

---

## 7. Errors

```python
class ErrorEnvelope(BaseModel):
    code: str                  # "profile.has_data", "training.cuda_oom", ...
    message: str
    details: list[FieldError] | None = None
    request_id: str

class FieldError(BaseModel):
    loc: list[str]
    msg: str
```

Error codes are stable strings; the SPA surface maps them to toast
messages and field-level errors. See
[`11-notifications.md`](11-notifications.md).

---

## 8. OpenAPI export gate

```
make openapi-export
```

Runs `python -m pdomain_ocr_trainer_spa.scripts.export_openapi` →
`frontend/openapi.json` → `openapi-typescript` →
`frontend/src/api/types.ts`. CI enforces `git diff --exit-code` after
re-running. Mirrors labeler-spa.

---

## 9. Citations

- Path / profile constants: `pd-ocr-trainer/src/pd_ocr_trainer/dataset_store.py:18-54`.
- Profile listing: `dataset_store.py:104-122`.
- Legacy migration: `dataset_store.py:192-200+`.
- `ITrainingRunner` / `TrainingEvent` / config models:
  `pdomain-ocr-training/pdomain_ocr_training/protocols.py:58-247`.
- `LocalTrainingRunner` (in-process thread, no cancellation):
  `pdomain-ocr-training/pdomain_ocr_training/local.py:253-420`.
- `ExportManager` dataset layout + import-time side effects:
  `pdomain-ocr-training/pdomain_ocr_training/datasets.py:19-58, 242-609`.
- `LongJobRunner` Protocol + `LocalLongJobRunner.submit_with_process`:
  `pdomain-ocr-ops/pdomain_ocr_ops/gpu/protocols.py:27-45`,
  `pdomain-ocr-ops/pdomain_ocr_ops/gpu/local_jobs.py:104-272`.
- Suite `mount_routes`: `pdomain-ocr-ops/pdomain_ocr_ops/suite/routes.py:14`.
