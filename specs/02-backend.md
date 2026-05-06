# 02 — Backend

FastAPI module layout, the `build_app(settings)` factory, every
adapter Protocol, and the full route map.

> Required reading: [`00-overview.md`](00-overview.md),
> [`01-data-models.md`](01-data-models.md). For long jobs see
> [`10-jobs-and-sse.md`](10-jobs-and-sse.md).

---

## 1. Module layout

```
src/pd_ocr_trainer_spa/
├── __init__.py
├── __main__.py                # uvicorn entry; reads env, calls build_app, runs server
├── bootstrap.py               # build_app(settings) factory
├── settings.py                # Settings (pydantic-settings)
├── core/
│   ├── app_state.py           # AppState dataclass + get_app_state dep
│   ├── job_runner.py          # see 10-jobs-and-sse.md
│   ├── notifications.py       # ring buffer + SSE bus (see 11-notifications.md)
│   ├── paths.py               # OS-aware roots (verbatim port of dataset_store path logic)
│   └── errors.py              # ErrorCode + HTTPException helpers
├── adapters/
│   ├── storage/__init__.py    # IStorage Protocol
│   ├── storage/filesystem.py  # default impl
│   ├── storage/s3.py          # NotImplementedYet
│   ├── auth/__init__.py       # IAuth Protocol + none
│   ├── training/__init__.py   # ITrainingRunner Protocol
│   ├── training/local_subprocess.py
│   ├── training/modal.py      # NotImplementedYet
│   ├── training/shared_container.py  # NotImplementedYet
│   ├── dataset_sources/__init__.py
│   ├── dataset_sources/local.py
│   ├── dataset_sources/huggingface.py
│   ├── model_registry/__init__.py
│   ├── model_registry/filesystem.py
│   └── model_registry/huggingface_hub.py
├── domain/
│   ├── profiles.py            # Profile, ProfileCounts, profile.toml IO
│   ├── datasets.py            # DatasetView assembly, kanban move logic
│   ├── runs.py                # Run model + on-disk persistence
│   ├── models.py              # TrainedModel discovery, sidecar IO
│   └── publish.py             # HF publish orchestration
├── api/
│   ├── healthz.py             # GET /healthz
│   ├── env_js.py              # GET /env.js (build version, feature flags)
│   ├── profiles.py            # /api/profiles/...
│   ├── datasets.py            # /api/profiles/{p}/datasets/...
│   ├── runs.py                # /api/runs/...
│   ├── jobs.py                # /api/jobs/{id}/events SSE
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
    training_runner_kind: Literal["local_subprocess", "modal", "shared_container"] = "local_subprocess"
    model_registry_kind: Literal["filesystem", "huggingface_hub"] = "filesystem"

    # HF
    hf_token_path: Path | None = None     # default: ~/.huggingface/token
    hf_default_owner: str | None = None   # e.g. "ntw8532"
    hf_cache_dir: Path | None = None      # maps to HF_HOME

    # Server
    host: str = "127.0.0.1"
    port: int = 8081                       # different default from labeler-spa (8080) so both can coexist
    cors_allow_origins: list[str] = ["http://localhost:5173"]   # vite dev
    log_level: str = "INFO"

    # Feature flags
    enable_typeface_training: bool = True
    enable_glyph_training: bool = True
    enable_hf_publish: bool = False        # gated behind explicit opt-in until M-HF-Publish ships

    @model_validator(mode="after")
    def _resolve_paths(self) -> "Settings":
        # absolute, expanduser, mkdir-as-needed for the writeable ones
        ...
```

Defaults match the legacy trainer's `dataset_store.py:18-54` — same
OS-aware fallbacks, same env var precedence. Renamed prefix from
`PD_OCR_TRAINER_*` to `PD_OCR_TRAINER_SPA_*` so both binaries can run
in the same shell with different roots if the user wants.
([Q7](../OPEN_QUESTIONS.md))

---

## 3. `build_app(settings)` factory

```python
def build_app(settings: Settings) -> FastAPI:
    app = FastAPI(
        title="pd-ocr-trainer-spa",
        version=_version.__version__,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_allow_origins, ...)

    storage = _build_storage(settings)
    auth = _build_auth(settings)
    training_runner = _build_training_runner(settings)
    dataset_sources = _build_dataset_sources(settings)
    model_registry = _build_model_registry(settings)

    state = AppState(
        settings=settings,
        storage=storage, auth=auth, training_runner=training_runner,
        dataset_sources=dataset_sources, model_registry=model_registry,
    )
    state.hydrate_from_disk()
    app.state.app_state = state

    app.include_router(healthz.router)
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

### 4.3 `ITrainingRunner`

```python
class ITrainingRunner(Protocol):
    def start(
        self,
        run: Run,
        on_event: Callable[[JobEvent], None],
        cancellation: CancellationToken,
    ) -> int: ...
    """
    Spawn the training subprocess (or remote job). Stream stdout/stderr
    line-by-line into on_event as JobEvent.log(...). Emit progress
    events when parseable. Return the exit code on terminal.
    Honour cancellation: best-effort SIGTERM then SIGKILL after grace.
    """
```

The `local_subprocess` impl spawns
`python -m pd_ocr_trainer.train_<task> --args-from runs/<id>/args.json`
(or whatever the trainer's preferred CLI shape is — see
[Q3](../OPEN_QUESTIONS.md) on extracting `pd-ocr-trainer-core`).
Stdout/stderr go to `runs/<id>/{stdout,stderr}.log`. Progress is
parsed with a regex per training script (each emits
`epoch X/Y` or similar). The parser config lives next to the
training command in `adapters/training/parsers.py`.

`modal` and `shared_container` impls raise `NotImplementedYet`.

### 4.4 `IDatasetSource`

```python
class IDatasetSource(Protocol):
    name: str           # "local" | "huggingface"
    def list(self, profile: str, task: TaskEnum, split: SplitEnum) -> Iterator[DatasetPageRef | DatasetCropRef]: ...
    def fetch_to_local(self, profile: str, task: TaskEnum, split: SplitEnum) -> Path: ...
    """Materialize the source data into a local DocTR-compatible directory and return its path."""
```

`local` impl wraps the existing `dataset_store.py` IO.
`huggingface` impl wraps `datasets.load_dataset` + the DocTR adapter
(per ROADMAP milestone (a)).

### 4.5 `IModelRegistry`

```python
class IModelRegistry(Protocol):
    def list(self) -> list[TrainedModel]: ...
    def get(self, name: str) -> TrainedModel | None: ...
    def write_artefacts(self, run: Run, paths: ModelPaths, sidecar: ModelSidecar) -> TrainedModel: ...
    def publish(self, model: TrainedModel, repo: str, on_event: Callable[[JobEvent], None]) -> ModelPublication: ...
```

`filesystem` impl manages `<shared-models>/<profile>/<task>/...`
exactly the way `dataset_store.model_output_dir()` does today.
`huggingface_hub` impl wraps `HfApi.upload_large_folder` and the
existing `push_to_hf_hub` codepath in `train_detect.py` /
`train_recog.py`. ([Q8](../OPEN_QUESTIONS.md))

---

## 5. Full route map

> Conventions: all paths under `/api`. JSON in/out except where SSE is
> noted. `404` if any path-segment entity is unknown. `409` for
> conflicting concurrent state. `422` for Pydantic validation. `500`
> only on truly unexpected internal errors. All errors are
> `ErrorEnvelope` (see §6).

### 5.1 Health / build info

| Method | Path | Body | Returns | Notes |
|---|---|---|---|---|
| GET | `/healthz` | — | `{"status":"ok"}` | Used by Docker probes. |
| GET | `/env.js` | — | JS file | Inlines `__APP_ENV__ = {version, features}` for the SPA. |

### 5.2 Profiles (`api/profiles.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/profiles` | — | `list[Profile]` |
| GET | `/api/profiles/{name}` | — | `Profile` |
| POST | `/api/profiles` | `CreateProfileRequest{name, display_name?, language?, typeface?}` | `Profile` (201) |
| PATCH | `/api/profiles/{name}` | `UpdateProfileRequest{display_name?, language?, typeface?}` | `Profile` |
| DELETE | `/api/profiles/{name}` | — | `204`. Refuses if any data lives under the profile (`409 profile.has_data`). |
| POST | `/api/profiles/migrate-legacy` | — | `{moved_paths: [...]}` |

`POST /api/profiles/migrate-legacy` triggers
`migrate_legacy_dataset_layout()`. Legacy
`base-ocr` → `all` rename happens implicitly on first
`/api/profiles` GET; explicit endpoint exists for tests.

### 5.3 Datasets (`api/datasets.py`)

All under `/api/profiles/{profile}` prefix. Concrete paths:

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/profiles/{profile}/datasets/{task}/kanban` | — | `KanbanView` (3 columns × N rows) |
| POST | `/api/profiles/{profile}/datasets/{task}/move` | `MoveRequest{from, to, page_keys[]}` | `KanbanView` |
| POST | `/api/profiles/{profile}/datasets/{task}/move-pages` | batch variant | same |
| POST | `/api/profiles/{profile}/datasets/{task}/move-crops` | batch variant | same |
| POST | `/api/profiles/{profile}/datasets/{task}/include-toggles` | `{include_detection: bool, include_recognition: bool}` | `KanbanView` |
| POST | `/api/profiles/{profile}/datasets/{task}/scan` | — | `KanbanView` (forces re-scan of export root + on-disk) |

The kanban semantics live in [`05-dataset-kanban.md`](05-dataset-kanban.md).

### 5.4 Runs (`api/runs.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/runs` | — | `list[Run]` (paginated; default 100) |
| GET | `/api/runs/{run_id}` | — | `Run` |
| POST | `/api/runs` | `CreateRunRequest{profile, task, kind, args, dataset_sources}` | `Run` (202; includes `job_id`) |
| POST | `/api/runs/{run_id}/cancel` | — | `Run` (status → `cancelled` once subprocess dies) |
| GET | `/api/runs/{run_id}/log` | `?stream=stdout|stderr&from_byte=N` | `text/plain` (tail) |
| DELETE | `/api/runs/{run_id}` | — | `204`. Refuses if running. |

### 5.5 Jobs (`api/jobs.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/jobs/{job_id}` | — | `Job` |
| GET | `/api/jobs/{job_id}/events` | — | `text/event-stream` (SSE) |

SSE event shapes: see [`10-jobs-and-sse.md`](10-jobs-and-sse.md).

### 5.6 Eval (`api/eval.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/eval` | `EvalRequest{profile, task, model_name?, val_source?}` | `Run` (kind=`eval`) |
| GET | `/api/eval/{run_id}/result` | — | `EvalResult` (CER/WER overall + sliced; see [`07-evaluation-and-metrics.md`](07-evaluation-and-metrics.md)) |

### 5.7 Models (`api/models.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/models` | `?profile=&task=` | `list[TrainedModel]` |
| GET | `/api/models/{name}` | — | `TrainedModel` |
| GET | `/api/models/{name}/sidecar` | — | `ModelSidecar` |
| POST | `/api/models/{name}/rename` | `{new_name}` | `TrainedModel` |
| DELETE | `/api/models/{name}` | — | `204`. |

### 5.8 Sources (`api/sources.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/sources` | — | `list[DatasetSourceInfo]` |
| GET | `/api/sources/{name}/profiles/{profile}/datasets/{task}/preview` | — | first ~50 rows for kanban preview when `huggingface` source is configured |

### 5.9 Publish (`api/publish.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/publish/dataset` | `PublishDatasetRequest{profile, task, repo, visibility}` | `Run` (kind=`publish-dataset`) |
| POST | `/api/publish/model` | `PublishModelRequest{model_name, repo, visibility}` | `Run` (kind=`publish-model`) |

Both gated by `Settings.enable_hf_publish`. Returns `403
publish.disabled` when off.

### 5.10 Settings (`api/settings.py`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/settings` | — | `PublicSettings` (paths, feature flags, vocabs cache info) |
| GET | `/api/settings/vocabs` | — | `dict[str, str]` (DocTR `VOCABS` map; cached per ui.py:74) |

---

## 6. Errors

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

Error codes are stable strings; the SPA surface maps them to
toast messages and field-level errors. See
[`11-notifications.md`](11-notifications.md).

---

## 7. OpenAPI export gate

```
make openapi-export
```

Runs `python -m pd_ocr_trainer_spa.scripts.export_openapi` →
`frontend/openapi.json` → `openapi-typescript` →
`frontend/src/api/types.ts`. CI enforces `git diff --exit-code` after
re-running. Mirrors labeler-spa.

---

## 8. Citations

- Path / profile constants: `pd-ocr-trainer/src/pd_ocr_trainer/dataset_store.py:18-54`.
- Profile listing: `dataset_store.py:104-122`.
- Legacy migration: `dataset_store.py:192-200+`.
- VOCABS cache: `pd-ocr-trainer/src/pd_ocr_trainer/ui.py:74-100`.
- Training subprocess pattern: `train_detect.py` and `train_recog.py`.
