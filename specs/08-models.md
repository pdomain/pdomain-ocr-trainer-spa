# 08 — Models

The model registry, sidecar format, naming convention, and on-disk
layout. HF push is in [`09-hf-integration.md`](09-hf-integration.md);
this spec covers everything local + the registry abstraction.

> Required reading: [`01-data-models.md`](01-data-models.md) §5,
> [`02-backend.md`](02-backend.md) §5.7.

---

## 1. Where models live on disk

The legacy trainer writes model artefacts under:

```
<shared-models-dir>/<profile>/<task>/<model_name>/
  ├── model.pt | model.safetensors    # weights
  ├── config.json                      # arch + hparams (DocTR-shaped)
  ├── train_metrics.json               # loss curves, captured by trainer
  ├── <model_name>.metadata.json       # SPA-introduced sidecar (see §3)
```

`<shared-models-dir>` defaults to the OS-aware data dir
(`get_os_data_parent() / "pd-ml-models"`,
`pd-ocr-trainer/src/pd_ocr_trainer/dataset_store.py:46`); the SPA
reads the same `Settings.shared_models_dir`.

The SPA does **not** invent a new directory layout. `IModelRegistry.filesystem`
walks `<shared-models-dir>/*/*/*/` and infers `(profile, task,
model_name)` from the path.

A model's "presence" is the existence of a recognised weights file
(`model.pt`, `model.safetensors`, or future `pytorch_model.bin`) in
the leaf dir. Sidecar absence is allowed (the SPA shows "Sidecar
missing — regenerate?" when so).

---

## 2. Naming convention

Two forms coexist:

| Form | Example | Status |
|---|---|---|
| Legacy | `pd-clogaelach-recognition-model-finetuned-2026-05-05` | **read-only**; SPA displays + evaluates + publishes but never mints |
| New (post-ROADMAP) | `pd-ga-clogaelach-recognition-2026-05-05` | minted by SPA; required for new HF publishes |

Parser/formatter lives in `frontend/src/lib/modelName.ts` and
`src/pdomain_ocr_trainer_spa/domain/models.py` — the two implementations
must round-trip the same set of strings.

```python
def parse_model_name(name: str) -> ParsedModelName: ...
@dataclass
class ParsedModelName:
    prefix: str           # "pd"
    language: str | None  # populated only on new form
    typeface: str | None  # populated only on new form
    profile: str | None   # populated only on legacy form
    task: str
    qualifier: str        # everything after the task slot, joined with "-"
    is_legacy: bool
```

A legacy name lacks `language` and `typeface` slots; the registry
back-fills them from the profile's `profile.toml` if the linked
profile is intact, leaving them `None` otherwise.

---

## 3. Sidecar format

The SPA writes `<model_name>.metadata.json` next to the weights on
every successful train run:

```json
{
  "name": "pd-ga-clogaelach-recognition-2026-05-05",
  "task": "recognition",
  "language": "ga",
  "typeface": "clogaelach",
  "trained_on": [
    {"repo": "local:ml-training/clogaelach/recognition", "revision": "fs:<sha256>", "rows": 1842, "weight": 1.0, "source": "local"}
  ],
  "doctr_arch": "crnn_vgg16_bn",
  "trainer_version": "0.x.y",
  "trained_at": "2026-05-05T18:00:00Z",
  "args": {...},                          // verbatim subprocess args
  "eval": {                               // optional — populated when an eval run finished against this model
    "best_run_id": "01HW...",
    "overall": { "cer": 0.034, "wer": 0.092 }
  }
}
```

Verbatim from `pd-ocr-trainer/docs/ROADMAP.md` §Model metadata
sidecar with `args` and `eval` additions for the SPA. Schema is
**append-only** by convention; new fields land as optional, never
breaking older readers ([Q6](../OPEN_QUESTIONS.md): explicit
`sidecar_schema: int` for safety?).

For local sources, `revision` is `"fs:<sha256-of-labels-and-image-mtimes>"`
— a stable hash over `labels.json` + per-file mtimes. For HF
sources, `revision` is the commit hash returned by `datasets.load_dataset(revision=...)`.

---

## 4. Sidecar regeneration

If a sidecar is missing or stale (e.g. user renamed a directory by
hand), `POST /api/models/{name}/regenerate-sidecar` runs:

1. Walks the on-disk leaf dir, infers task + arch from `config.json`.
2. Finds the most-recent `Run` with matching `model_name`; copies
   `args`, `trained_on`, `trained_at` from its manifest.
3. Falls back to inferred-only when no run matches; surfaces a
   warning "sidecar incomplete — train_on data unavailable".

---

## 5. Endpoints

```
GET    /api/models                               → list[TrainedModel]
       query: ?profile=&task=&include_legacy=true
GET    /api/models/{name}                        → TrainedModel
GET    /api/models/{name}/sidecar                → ModelSidecar
POST   /api/models/{name}/regenerate-sidecar     → TrainedModel
PATCH  /api/models/{name}                         body: {language?, typeface?, qualifier?}
       # Updates the sidecar only (no on-disk rename).
DELETE /api/models/{name}                         → 204
       # Refuses if model is referenced by a non-terminal Run (e.g. an in-progress eval).
POST   /api/models/{name}/rename                  body: {new_name}  → TrainedModel
       # Renames both the leaf directory and the sidecar; updates last-known-name in any Run that referenced the old one.
```

Rename rules:

- New name must follow the new naming convention or be an explicit
  legacy name. Free-form names rejected (`422 model.invalid_name`).
- New name must not exist already (`409 model.name_taken`).
- Rename is atomic on POSIX; two-phase on Windows with a temp
  suffix.

---

## 6. Model-list page

Route: `/models`.

- Table: name | profile | task | language | typeface | best CER/F1 | last trained | actions.
- Filters: profile (multi), task (multi), legacy (yes/no/both).
- Sort: by `last_trained` desc default; click any header to sort.
- Row click → `/models/{name}`.
- Bulk actions: `[Delete]`, `[Publish to HF]` (gated by feature flag).

---

## 7. Model-detail page

Route: `/models/{name}`.

```
┌────────────────────────────────────────────────────────────────┐
│  Header: pd-ga-clogaelach-recognition-2026-05-05               │
│  Profile: clogaelach · Task: recognition                        │
│  Language: ga · Typeface: clogaelach                            │
│  [Open Eval] [Rename] [Publish to HF] [Delete]                 │
├────────────────────────────────────────────────────────────────┤
│  Sidecar (collapsible JSON view)                                │
│  Best Eval (linked to /runs/{run_id})                           │
│  Trained from (per-source: repo, revision, rows, weight)        │
│  Args (collapsible)                                             │
├────────────────────────────────────────────────────────────────┤
│  Runs against this model                                        │
│  - eval runs (status, started_at, CER/WER, link)                │
└────────────────────────────────────────────────────────────────┘
```

---

## 8. Model registry caching

`IModelRegistry.filesystem` caches the model list with a 30 s TTL
plus an inotify-style mtime check on `<shared-models-dir>`. Forced
refresh via `POST /api/models/scan`.

For the HF impl (see [`09-hf-integration.md`](09-hf-integration.md)),
list is **on-demand only** — never automatic; the SPA only queries
HF when the user opens the publish dialog.

---

## 9. Acceptance behaviour

1. Successful detection train run finishes. The model artefacts
   land at `<shared-models-dir>/clogaelach/detection/<name>/`. The
   sidecar lives next to them. `GET /api/models?profile=clogaelach`
   returns the new model.
2. Rename the model to a new-form name. The directory renames; the
   sidecar updates; `GET /api/runs?model_name=<old>` no longer
   returns the run, but `GET /api/runs?model_name=<new>` does.
3. Manually delete the sidecar from disk. The model still appears
   in `/models`, with a yellow "sidecar missing" indicator. Click
   "Regenerate sidecar"; status normalizes.
4. Delete the model. The directory is removed. Any `Run` records
   that referenced it are kept but their `artefact_paths` show as
   "missing".

---

## 10. Citations

- Shared-models dir constant: `pd-ocr-trainer/src/pd_ocr_trainer/dataset_store.py:46`.
- Model output dir helper: `dataset_store.py:73-74`.
- Legacy model-name prefixing: `pd-ocr-trainer/src/pd_ocr_trainer/ui.py:247-259`.
- Sidecar shape: `pd-ocr-trainer/docs/ROADMAP.md` §Model metadata sidecar.
