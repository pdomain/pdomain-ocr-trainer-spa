# 01 — Data models

The wire models on the REST surface, the on-disk shapes the trainer
reads and writes, and the in-memory `AppState` graph.

> **Scope.** This spec defines schemas. Endpoint contracts are in
> [`02-backend.md`](02-backend.md); kanban semantics are in
> [`05-dataset-kanban.md`](05-dataset-kanban.md); model-sidecar
> details are in [`08-models.md`](08-models.md).

All wire models are **Pydantic v2**. JSON snake_case both directions —
the OpenAPI generator picks up Python field names. Reserved fields
end with `_`, never start.

---

## 1. Profile

A "profile" (a.k.a. "group") is the unit of training data isolation:
detection + recognition + (optional) typeface + (optional) glyph
training data, all aligned, plus a target prefix for trained models.
The legacy code calls profiles "groups" in the UI and "profiles" in
the API; we standardize on **profile** everywhere
(`pdomain-ocr-training/src/pdomain_ocr_training/dataset_store.py:24`).

```python
class Profile(BaseModel):
    """A training-data profile. The unit of isolation between training runs."""
    name: str                     # normalized: lowercase, hyphenated. e.g. "all", "italics", "clogaelach"
    display_name: str             # original case from disk, e.g. "Cló Gaelach"
    language: str | None = None   # BCP-47, e.g. "en", "ga". None until set; required at publish.
    typeface: TypefaceEnum | None = None  # closed enum (see §1.1). None until set.
    is_base: bool                 # True only for "all" / "base-ocr" (legacy alias)
    has_training_data: bool       # any (detection|recognition) labels exist under ml-training/<name>/
    has_validation_data: bool     # any (detection|recognition) labels exist under ml-validation/<name>/
    counts: ProfileCounts         # per-task page/crop counts, populated lazily

class ProfileCounts(BaseModel):
    detection_train_pages: int
    detection_val_pages: int
    recognition_train_crops: int
    recognition_val_crops: int
    typeface_train_crops: int = 0
    typeface_val_crops: int = 0
    glyph_train_crops: int = 0
    glyph_val_crops: int = 0
```

### 1.1 TypefaceEnum

Mirrors `pdomain-ocr-training/docs/ROADMAP.md` §"Typeface enum". Closed.

```python
class TypefaceEnum(str, Enum):
    roman = "roman"
    italic = "italic"            # word-level only — no detect/recog repos
    smallcaps = "smallcaps"      # word-level only — no detect/recog repos
    blackletter = "blackletter"
    fraktur = "fraktur"
    clogaelach = "clogaelach"
    greek = "greek"
    greek_classical = "greek-classical"
    typeface = "typeface"        # literal — only for typeface-classifier dataset/model
```

The literal `typeface` value is **only** valid on classifier datasets
and classifier models, and is rejected when set on a detection or
recognition profile that's about to be published. The SPA validates
this at publish time, never at profile-create time. ([Q4](../OPEN_QUESTIONS.md))

### 1.2 On-disk profile state

Profiles are not first-class on disk. They are inferred from:

- `ml-training/<name>/{detection,recognition,typeface,glyph}/` directories,
- `ml-validation/<name>/{detection,recognition,typeface,glyph}/` directories,
- `<shared-models>/<name>/` model output directories,
- the labeler's DocTR export root scan
  (`iter_export_profile_dirs(export_root)`).

`language` and `typeface` live in a per-profile **`profile.toml`**
sidecar at `ml-training/<name>/profile.toml` (and mirrored in
`ml-validation/<name>/profile.toml`). The legacy trainer doesn't
write this file; the SPA introduces it. Both files must agree on
load — disagreement is a 409 `profile.toml.conflict` error from the
backend, surfaced as a toast with a "Resolve" link. ([Q5](../OPEN_QUESTIONS.md))

```toml
# ml-training/clogaelach/profile.toml
language = "ga"
typeface = "clogaelach"
display_name = "Cló Gaelach"
```

---

## 2. Dataset

Datasets are *derived* from profiles + tasks; they are not their own
on-disk noun. The wire model reflects what the kanban renders.

```python
class DatasetView(BaseModel):
    profile: str
    task: TaskEnum                # see §2.1
    split: SplitEnum              # "train" | "val" | "unassigned"
    pages: list[DatasetPageRef]   # for detection
    crops: list[DatasetCropRef] | None = None  # for recognition / typeface / glyph

class DatasetPageRef(BaseModel):
    project_id: str               # e.g. "projectID63ac6757567bd"
    page_name: str                # e.g. "projectID63ac6757567bd_37.png"
    width: int
    height: int
    label_bbox_count: int         # number of GT bboxes
    in_split: SplitEnum           # mirrors enclosing split for self-describing rows
    style_tags: list[str]         # per-export-group style tags (see ROADMAP, e.g. "italics")

class DatasetCropRef(BaseModel):
    project_id: str
    crop_name: str                # e.g. "projectID..._37_0_3_2.png"
    page_name: str                # the parent detection page (recovered via detection_page_from_recognition_name)
    label_text: str
    style_tags: list[str]

class TaskEnum(str, Enum):
    detection = "detection"
    recognition = "recognition"
    typeface_classification = "typeface-classification"
    glyph_classification = "glyph-classification"

class SplitEnum(str, Enum):
    unassigned = "unassigned"     # in export root, not yet copied into ml-training / ml-validation
    train = "train"
    val = "val"
```

### 2.1 On-disk shape (read from / written to disk verbatim)

- **Detection.** `ml-{training,validation}/<profile>/detection/{images/, labels.json}`.
  `labels.json` is a `dict[image_name, list[bbox_dict]]`.
- **Recognition.** `ml-{training,validation}/<profile>/recognition/{images/, labels.json}`.
  `labels.json` is a `dict[crop_image_name, label_text]`.
- **Typeface classification.** `ml-{training,validation}/<profile>/typeface/{images/, metadata.jsonl}`.
  Each `metadata.jsonl` line: `{"file_name": "...png", "typeface": "roman"}`.
- **Glyph classification.** `ml-{training,validation}/<profile>/glyph/{images/, metadata.jsonl}`.
  Each line: `{"file_name": "...png", "ligatures": [...], "long_s": bool, "swash": bool}`.

The SPA is a thin wrapper over these shapes — it does not introduce
a new container format. See `pdomain-ocr-training/docs/DATASETS.md`.

### 2.2 Source pages (Unassigned)

The "Unassigned" column is populated by walking the labeler DocTR
export root (`ExportManager.get_export_root()` →
`iter_export_profile_dirs`). Each project / subfolder pair becomes a
group of `DatasetPageRef` rows.

---

## 3. Run

A single training-or-eval invocation. Persisted on disk so a run
survives an SPA restart.

```python
class Run(BaseModel):
    id: str                       # ulid; stable across restarts. Also the directory name under runs/.
    profile: str
    task: TaskEnum
    kind: RunKind                 # "train" | "eval" | "publish-dataset" | "publish-model"
    status: RunStatus             # see §3.1
    args: dict                    # the resolved CLI args dict (epochs, batch_size, vocab, ...). Schema per task.
    started_at: datetime
    finished_at: datetime | None
    exit_code: int | None
    artefact_paths: list[str]     # absolute paths emitted on success (model files, sidecar, dataset snapshot)
    job_id: str | None            # the pdomain-ocr-ops LongJobRunner job for this run, if any

class RunKind(str, Enum):
    train = "train"
    eval = "eval"
    publish_dataset = "publish-dataset"
    publish_model = "publish-model"

class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
```

### 3.1 On-disk shape

```
<app-data-root>/runs/<run_id>/
├── manifest.json        # serialized Run model
├── args.json            # exact subprocess args used
├── stdout.log           # captured stdout, line-buffered
├── stderr.log
├── progress.jsonl       # one line per progress event (see 10-jobs-and-sse.md)
└── artefacts/           # symlinks (or copies on Windows) to model output dir, sidecars, etc.
```

Hydrated on startup. `status` is **always** recomputed from on-disk
`manifest.json` + the absence of a live job in the registry (any run
in `running` state at boot with no live job becomes `failed` with
exit code `-1` and a synthetic `stderr.log` line "process gone").

---

## 4. Job

The SPA `Job` is a **projection of the `pdomain-ocr-ops` `JobStatus`**
(D-T20). The SPA does not own a job runner; `api/jobs.py` projects
`LongJobRunner.status(job_id)` onto this model. See
[`10-jobs-and-sse.md`](10-jobs-and-sse.md) §3 for the projection and
§4 for the event stream.

```python
class Job(BaseModel):
    id: str                       # = JobStatus.job_id
    run_id: str | None            # resolved from the runs registry by job_id
    kind: str                     # "train.detection", "publish.dataset", ...
    state: JobState
    progress: float               # 0.0 ≤ v ≤ 1.0 (= JobStatus.progress)
    error: str | None             # = JobStatus.error (plain string; last stderr line)
    started_at: datetime | None
    finished_at: datetime | None

class JobState(str, Enum):
    """Mirrors pdomain-ocr-ops JobStatus.state exactly."""
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
```

The structured event payloads (`progress` / `metric` / `log` /
`state`) are the `pdomain-ocr-ops` `JobEvent` shape — defined in
[`10-jobs-and-sse.md`](10-jobs-and-sse.md) §2, not duplicated here.

---

## 5. Model

A trained model artefact + its sidecar.

```python
class TrainedModel(BaseModel):
    name: str                     # full prefixed name, e.g. "pd-en-roman-detection-2026-05-05"
    profile: str
    task: TaskEnum
    language: str | None
    typeface: TypefaceEnum | None
    paths: ModelPaths
    sidecar: ModelSidecar
    published_to: list[ModelPublication]   # populated when pushed to HF

class ModelPaths(BaseModel):
    weights: str                  # absolute path to .pt / .safetensors
    sidecar: str                  # absolute path to <name>.metadata.json
    config: str | None = None

class ModelSidecar(BaseModel):
    """Verbatim port of pdomain-ocr-training/docs/ROADMAP.md §Model metadata sidecar."""
    name: str
    task: str                     # "detection" | "recognition" | "typeface-classification" | "glyph-classification"
    language: str
    typeface: str                 # closed enum value or the literal "typeface"
    trained_on: list[TrainedOnEntry]
    doctr_arch: str | None = None
    trainer_version: str
    trained_at: datetime

class TrainedOnEntry(BaseModel):
    repo: str                     # "<owner>/pd-ocr-..."
    revision: str                 # git commit / tag
    rows: int
    weight: float                 # mixing weight in [0, 1]
    source: Literal["local", "huggingface"] = "huggingface"

class ModelPublication(BaseModel):
    repo: str                     # e.g. "ntw8532/pd-en-roman-detection"
    revision: str
    pushed_at: datetime
```

### 5.1 Naming convention

Names are emitted by `_prefixed_model_name()` (legacy
`pdomain-ocr-training/src/pdomain_ocr_training/ui.py:247`). The SPA standardizes
on the **new** convention from the trainer ROADMAP §Cross-repo
dependencies:

```
pd-<lang>-<typeface>-<task>-<YYYY-MM-DD>[-<qualifier>]
```

Where `<task>` is one of `detection | recognition | typeface-classification | glyph-classification`.

The legacy `pd-<profile>-<task>-...` form is **read-only**: the SPA
will display, evaluate, and publish models that exist under the old
name, but never mints new names in the legacy form. This matches
ROADMAP milestone (d) "Cut the local-only path".

---

## 6. AppState (in-memory)

```python
@dataclass
class AppState:
    settings: Settings
    storage: IStorage
    auth: IAuth
    dataset_sources: list[IDatasetSource]
    model_registry: IModelRegistry
    job_runner: LongJobRunner               # pdomain-ocr-ops; owns job lifecycle (D-T20)

    profiles: dict[str, Profile]            # by normalized name
    runs: dict[str, Run]                    # by run id
    notifications: deque[Notification]      # ring buffer

    # cache: read-through; invalidated on directory mtime change
    _dataset_views: TTLCache[str, DatasetView]
```

Lives at `app.state.app_state`; routes get it via
`Depends(get_app_state)`. See [`02-backend.md`](02-backend.md) §Factory.

---

## 7. UserPrefs (frontend, browser-local)

Persisted per-browser via `zustand persist`. Not on the wire.

```ts
interface UserPrefs {
  selectedProfile: string;            // last-selected profile name
  kanbanFilters: {
    showOnlyMissing: boolean;
    styleTagFilter: string | null;
  };
  logViewer: {
    autoScroll: boolean;
    wrap: boolean;
  };
  splitter: {
    leftPx: number;
  };
}
```

---

## 8. Forward-compatibility rules

- Adding a field to a wire model: optional, default-valued. No version
  bump needed.
- Removing or renaming a field: breaking. Bump `OpenAPI info.version`.
- Adding a `RunKind` or `TaskEnum`: tolerated by older clients; they
  drop the unknown row from list views.
- Sidecar schema changes follow the same rule. The sidecar carries
  no version field by design — the schema is append-only.
  ([Q6](../OPEN_QUESTIONS.md): do we add an explicit
  `sidecar_schema: int` for safety?)

---

## 9. Citations

- Profile / dataset roots: `pdomain-ocr-training/src/pdomain_ocr_training/dataset_store.py:18-54`.
- Profile normalization: `dataset_store.py:62-66`.
- Existing-by-project grouping: `dataset_store.py:148-165`.
- Model-name prefix: `pdomain-ocr-training/src/pdomain_ocr_training/ui.py:247`.
- Sidecar shape: `pdomain-ocr-training/docs/ROADMAP.md` §Model metadata sidecar.
- Typeface enum: `pdomain-ocr-training/docs/ROADMAP.md` §Typeface enum.
- HF dataset shapes: `pdomain-ocr-training/docs/DATASETS.md` §Dataset shapes.
