# 04 — Profiles and OCR / training configuration

How profiles are listed, created, edited, deleted, and how the
OCR-config and training-config knobs from the legacy trainer surface
in the SPA.

> Required reading: [`01-data-models.md`](01-data-models.md),
> [`02-backend.md`](02-backend.md).

---

## 1. Profile lifecycle

### 1.1 Discovery (read-through, no DB)

`AppState.hydrate_from_disk()` discovers profiles by union of:

1. `ml-training/<name>/{detection,recognition,typeface,glyph}/` — any
   directory containing a recognized task subdir.
2. `ml-validation/<name>/...` — same rule.
3. `<shared-models>/<name>/` — any subdir with model weights.
4. The labeler export root (`ExportManager.get_export_root()`) — every
   `iter_export_profile_dirs(...)` subfolder name.

The union is normalized through `normalize_profile_name()`
(`pd-ocr-trainer/src/pd_ocr_trainer/dataset_store.py:62-66`):
lowercase, hyphenated, `base-ocr → all`, empty → `all`.

### 1.2 The `all` profile is special

- Always present, even on a fresh install.
- Cannot be deleted (`DELETE /api/profiles/all` → `409 profile.is_base`).
- Cannot have its `name` changed (no rename endpoint exists; it's
  derived from disk).
- `language` and `typeface` are optional on `all`; required on any
  profile that's about to publish a dataset or train a model that
  publishes.

### 1.3 Create

```
POST /api/profiles
{ "name": "Cló Gaelach",         // free-form; server normalizes
  "display_name": "Cló Gaelach", // optional; defaults to original input
  "language": "ga",              // optional at create time
  "typeface": "clogaelach"       // optional at create time
}
→ 201 Profile{ name="cló-gaelach", display_name="Cló Gaelach", ... }
```

The server creates `ml-training/<normalized>/`,
`ml-validation/<normalized>/`, and writes
`ml-training/<normalized>/profile.toml` (and the validation mirror)
if `language` or `typeface` were supplied. Empty `profile.toml` is
*not* written — absence of the file means "unset".

### 1.4 Edit

```
PATCH /api/profiles/{name}
{ "display_name"?: str, "language"?: str | null, "typeface"?: TypefaceEnum | null }
```

Setting `language: null` clears the field on disk (the file is
rewritten with the field removed; if both fields end up null the
sidecar file is deleted).

### 1.5 Delete

```
DELETE /api/profiles/{name}
```

Refuses (`409 profile.has_data`) if any of these exist:

- `ml-training/<name>/{any-task}/labels.json` or `metadata.jsonl`
- `ml-validation/<name>/{any-task}/labels.json` or `metadata.jsonl`
- `<shared-models>/<name>/` non-empty
- a `Run` with this profile in any non-terminal state

Successful delete:

1. Refuses if `name == "all"`.
2. Removes the empty `ml-training/<name>/` and
   `ml-validation/<name>/` directories.
3. Removes `<shared-models>/<name>/` only if it's empty after model
   removal (which the SPA does *not* do automatically).
4. Returns `204`.

### 1.6 Legacy migration

`POST /api/profiles/migrate-legacy` runs
`migrate_legacy_dataset_layout()`
(`dataset_store.py:192-200+`) to move `ml-training/{detection,recognition}/`
into `ml-training/all/{detection,recognition}/`. Idempotent. The SPA
calls it once on first boot, **and** exposes the endpoint so tests
can trigger it explicitly.

---

## 2. OCR configuration

The legacy trainer surfaces a vocab library + custom-characters set in
`RecognitionTrainingConfig` (`ui.py:291-318`). The SPA exposes the
same knobs but **at training-run time**, not as global state. Users
build a vocab in the run-creation form; the resolved
`CUSTOM:<chars>` string lives in `Run.args.vocab`.

### 2.1 Vocab library

The DocTR-bundled vocab dictionary is read once at backend startup
via `_get_vocabs()` (`ui.py:74-100`) and cached at
`<app-data-root>/_vocabs_cache.json`. Surfaced as:

```
GET /api/settings/vocabs → dict[name, characters]
```

Frontend caches with a 30-day stale time. The cache key changes only
when DocTR version changes; the SPA does not invalidate on every
request.

### 2.2 Custom characters

The default custom-characters string is `DEFAULT_CUSTOM_CHARACTERS`
from `pd_book_tools.ocr.doctr_support`. The SPA respects it as the
seed for new run forms but the *active* set lives only on the run
form state — there is no project-wide persisted "custom chars".

### 2.3 Missing-char scan

```
POST /api/profiles/{profile}/scan-missing-chars
{ "vocab_library": ["french", ...], "custom_characters": "..." }
→ { "missing": "ÀÁÂ..." }   // expanded with case pairs (ui.py:209-244)
```

Pure read-only on the recognition `labels.json`. Does not mutate
state. Wired to a button in the recognition run form ("Scan training
set for missing chars").

---

## 3. Training configuration

### 3.1 The legacy state, decomposed

`pd-ocr-trainer/src/pd_ocr_trainer/ui.py:267-318` defines two
config classes — `DetectionTrainingConfig` and
`RecognitionTrainingConfig` — held as **module-level singletons**
that the UI mutates and `_save_trainer_settings()` writes to
`TRAINER_SETTINGS_PATH`.

The SPA splits this into:

- **Per-profile training-config defaults** stored on disk at
  `<app-data-root>/profiles/<name>/training_defaults.json`. This is
  what gets pre-filled when the user opens the run-creation form for
  this profile + task.
- **Per-run frozen args** stored at `runs/<run_id>/args.json`. This
  is what the subprocess actually receives. Once a run starts, its
  args never change.

`training_defaults.json` is *advisory*: nothing else reads it.
Editing it never affects a running or completed run.

### 3.2 Schema per task

Detection (mirrors `DetectionTrainingConfig`, `ui.py:267-288`):

```json
{
  "arch": "db_resnet50",
  "epochs": 100,
  "batch_size": 2,
  "workers": 4,
  "learning_rate": 0.002,
  "weight_decay": 0.0,
  "optimizer": "adam",
  "scheduler": "poly",
  "input_size": 1024,
  "rotation": false,
  "amp": false,
  "pretrained": true,
  "early_stop": false,
  "early_stop_epochs": 5,
  "early_stop_delta": 0.01,
  "model_name_template": "model-finetuned-{date}"
}
```

Recognition (mirrors `RecognitionTrainingConfig`, `ui.py:291-318`):

```json
{
  "arch": "crnn_vgg16_bn",
  "epochs": 100,
  "batch_size": 64,
  "workers": 4,
  "learning_rate": 0.001,
  "weight_decay": 0.0,
  "optimizer": "adam",
  "scheduler": "cosine",
  "input_size": 32,
  "pretrained": true,
  "amp": false,
  "early_stop": false,
  "early_stop_epochs": 5,
  "early_stop_delta": 0.01,
  "vocab_library": ["french"],
  "custom_characters": "...",
  "model_name_template": "model-finetuned-{date}"
}
```

Typeface classification (new — mirrors trainer ROADMAP (a.5);
[Q9](../OPEN_QUESTIONS.md) on architecture):

```json
{
  "arch": "<TBD>",
  "epochs": 50,
  "batch_size": 128,
  "workers": 4,
  "learning_rate": 0.001,
  "input_size": 64,
  "amp": true,
  "model_name_template": "model-classifier-{date}"
}
```

Glyph classification (new — mirrors trainer ROADMAP (g2);
[Q10](../OPEN_QUESTIONS.md) on multi-head shape):

```json
{
  "arch": "<TBD>",
  "epochs": 50,
  "batch_size": 128,
  "workers": 4,
  "learning_rate": 0.001,
  "input_size": 48,
  "amp": true,
  "feature_heads": ["ligature_ct", "ligature_st", "long_s", "swash"],
  "model_name_template": "model-glyph-{date}"
}
```

### 3.3 Endpoint surface

```
GET  /api/profiles/{name}/training-defaults/{task}                 → defaults dict (404 → never edited; SPA falls back to seed)
PUT  /api/profiles/{name}/training-defaults/{task}                 → 200, persisted
DELETE /api/profiles/{name}/training-defaults/{task}                 → 204, falls back to seed
```

The seed defaults (when `training_defaults.json` is absent) match
the legacy `DetectionTrainingConfig.__init__` /
`RecognitionTrainingConfig.__init__` exactly. Code review checks
each seed value field-for-field against the legacy code.

### 3.4 GPU / batch-size auto-suggest

The legacy `_suggest_batch_size()` reads VRAM and picks a power-of-2
batch size (`ui.py:189-206`). The SPA exposes:

```
GET /api/runtime/suggest-batch-size?task=detection|recognition
→ { "vram_gb": 24.0, "suggested_batch_size": 16 }
```

The frontend offers the suggestion as a one-click "Use suggested" on
the batch-size field. Empty / no-GPU returns `vram_gb: 0`,
`suggested_batch_size: 1`.

### 3.5 Device selection

Detection / recognition device is set lazily at training start via
`_detect_cuda_device()` (`ui.py:288, 318`). The SPA exposes:

```
GET /api/runtime/devices
→ { "cuda": ["cuda:0", "cuda:1"], "mps": false, "cpu": true }
```

The run form lets the user pin a device or leave it on `auto`.
`auto` resolves on the backend at subprocess spawn.

---

## 4. Profile-toml format

Referenced from [`01-data-models.md`](01-data-models.md) §1.2.
Complete schema:

```toml
# ml-training/<profile>/profile.toml
display_name = "Cló Gaelach"          # optional
language = "ga"                       # optional, BCP-47
typeface = "clogaelach"               # optional, TypefaceEnum value
notes = "Imported from PGDP batch 3"  # optional, free-form
```

Reader: `tomllib` (stdlib in 3.11+). Writer: a tiny custom function
that emits exactly the four keys above in stable order; we don't
adopt a TOML writer dependency for this. Unknown keys are
**preserved verbatim** on round-trip (forward-compat); the writer
serializes them at the end of the file.

---

## 5. UI surface

`ProfilesPage` (route `/profiles`):

- Table with columns: name | display_name | language | typeface |
  detection counts | recognition counts | typeface counts | glyph
  counts | actions.
- "New profile" button opens `ProfileEditDialog` in create mode.
- Each row clickable → `/profiles/{name}`.
- Row hover shows a "..." menu: Edit, Delete (disabled if
  `is_base`), Migrate Legacy (visible only when legacy detection +
  recognition exist at `ml-training/`).

`ProfileDetailPage` (route `/profiles/{name}`):

- Header: profile name + language + typeface + edit pencil.
- Tabs: Datasets | Runs | Models.
- Datasets tab → embeds `DatasetsPage` for the default task
  (recognition).

`ProfileEditDialog`:

- Fields: display_name (text), language (combobox: free-form with
  BCP-47 hints), typeface (select from `TypefaceEnum` minus
  `typeface`), notes (textarea).
- On submit: PATCH (or POST in create mode), then invalidate
  `["profiles"]` and `["profile", name]`.

---

## 6. Acceptance behaviour

1. Fresh install boots, hits `/api/profiles`, shows exactly one row:
   `all`. ProfileCounts all zero.
2. Drop a single labeler export under the labeler's export root.
   Hit `POST /api/profiles/all/datasets/recognition/scan`. The
   project shows up in the Unassigned column.
3. Create profile `clogaelach` with `language=ga, typeface=clogaelach`.
   Confirm `ml-training/clogaelach/profile.toml` and
   `ml-validation/clogaelach/profile.toml` both exist with matching
   content.
4. PATCH `clogaelach` to clear typeface. Files retain language only.
   PATCH again to clear language. Both files are deleted.
5. Save training defaults for `clogaelach` recognition with
   `epochs: 50`. Reopen the run form: epochs prefills 50.
6. Delete `clogaelach`. The dirs go away, but `<shared-models>/`
   contents are untouched.

---

## 7. Citations

- Profile constants / discovery: `dataset_store.py:18-122`.
- Legacy migration: `dataset_store.py:192-200+`.
- DetectionTrainingConfig defaults: `ui.py:267-288`.
- RecognitionTrainingConfig defaults: `ui.py:291-318`.
- Vocab cache: `ui.py:74-100`.
- Missing-char scan: `ui.py:209-244`.
- Batch-size suggest: `ui.py:189-206`.
- Model-name prefix: `ui.py:247-259`.
