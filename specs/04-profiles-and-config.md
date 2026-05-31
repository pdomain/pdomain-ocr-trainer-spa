# 04 — Profiles and OCR / training configuration

How profiles are listed, created, edited, deleted, and how the
OCR-config and training-config knobs surface in the SPA.

> Required reading: [`01-data-models.md`](01-data-models.md),
> [`02-backend.md`](02-backend.md) §4.3.
>
> **Re-spec note (2026-05-21).** Training-config schemas are now
> aligned to `pdomain-ocr-training`'s `DetectionConfig` /
> `RecognitionConfig` (the typed, `torch`-free config models), not
> the legacy `ui.py` config classes. The UI surface references
> `pdomain-ui` components (D-T19). Dataset discovery uses
> `pdomain_ocr_training.datasets.ExportManager`.

---

## 1. Profile lifecycle

### 1.1 Discovery (read-through, no DB)

`AppState.hydrate_from_disk()` discovers profiles by union of:

1. `<ml_training_dir>/<name>/{detection,recognition,typeface,glyph}/`
   — any directory containing a recognized task subdir.
2. `<ml_validation_dir>/<name>/...` — same rule.
3. `<shared_models_dir>/<name>/` — any subdir with model weights.
4. The labeler export root — every export-profile subfolder name
   (`pdomain_ocr_training.datasets.ExportManager.get_export_root()`).

The union is normalized: lowercase, hyphenated, `base-ocr → all`,
empty → `all` (the `BASE_OCR_PROFILE` rule in
`pdomain_ocr_training.datasets`).

### 1.2 The `all` profile is special

- Always present, even on a fresh install.
- Cannot be deleted (`DELETE /api/profiles/all` → `409 profile.is_base`).
- Cannot be renamed (no rename endpoint; the name is derived from disk).
- `language` / `typeface` are optional on `all`; required on any
  profile about to train a model whose name is minted from
  profile metadata (D-T6, [`06-training-runs.md`](06-training-runs.md) §6).

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

The server creates `<ml_training_dir>/<normalized>/`,
`<ml_validation_dir>/<normalized>/`, and writes `profile.toml` to
both (§4) if `language` or `typeface` were supplied. An empty
`profile.toml` is *not* written — absence means "unset".

### 1.4 Edit

```
PATCH /api/profiles/{name}
{ "display_name"?: str, "language"?: str | null, "typeface"?: TypefaceEnum | null }
```

Setting a field to `null` clears it on disk (the file is rewritten
without the field; if both `language` and `typeface` end up null the
`profile.toml` is deleted). Both the training-side and
validation-side `profile.toml` are kept in sync (D-T5); a detected
mismatch at load is `409` ([Q5](../OPEN_QUESTIONS.md)).

### 1.5 Delete

```
DELETE /api/profiles/{name}
```

Refuses (`409 profile.has_data`) if any of these exist:

- `<ml_training_dir>/<name>/{any-task}/labels.json` or `metadata.jsonl`
- `<ml_validation_dir>/<name>/{any-task}/labels.json` or `metadata.jsonl`
- `<shared_models_dir>/<name>/` non-empty
- a `Run` with this profile in any non-terminal state

Successful delete refuses if `name == "all"`, removes the empty
training/validation directories, removes `<shared_models_dir>/<name>/`
only if empty, and returns `204`.

### 1.6 Legacy migration

`POST /api/profiles/migrate-legacy` moves the legacy flat
`<ml_training_dir>/{detection,recognition}/` layout into
`<ml_training_dir>/all/{detection,recognition}/`. Idempotent. The SPA
calls it once on first boot and also exposes the endpoint for tests.

---

## 2. OCR configuration

The recognition vocab + custom-character set surface **at
training-run time**, not as global state. The user builds a vocab in
the run-creation form; `training/config_build.py` resolves it into
the final `RecognitionConfig.vocab` string before the run is
submitted ([`02-backend.md`](02-backend.md) §4.3,
[`06-training-runs.md`](06-training-runs.md) §5.2).

### 2.1 Vocab library

```
GET /api/settings/vocabs → dict[name, characters]
```

The DocTR-bundled `VOCABS` map, resolved without importing `torch`
into the web process (a lazy helper / the worker), and cached at
`<app_data_root>/_vocabs_cache.json`. The frontend caches with a
30-day stale time; the cache key changes only with the DocTR
version.

### 2.2 Custom characters

The seed custom-characters string is `DEFAULT_CUSTOM_CHARACTERS` from
`pdomain_book_tools.ocr.doctr_support`. The SPA uses it as the seed for a
new recognition run form; the *active* set lives only on run-form
state — there is no project-wide persisted "custom chars".

### 2.3 Missing-char scan

```
POST /api/profiles/{profile}/scan-missing-chars
{ "vocab_library": ["french", ...], "custom_characters": "..." }
→ { "missing": "ÀÁÂ..." }   // expanded with case pairs
```

Pure read-only over the recognition `labels.json`. Wired to a button
in the recognition run form ("Scan training set for missing chars").

---

## 3. Training configuration

### 3.1 Two layers: per-profile defaults, per-run frozen args

- **Per-profile training-config defaults** at
  `<app_data_root>/profiles/<name>/training_defaults.json` — what
  pre-fills the run-creation form for this profile + task. Advisory:
  nothing else reads it; editing it never affects an existing run.
- **Per-run frozen args** at `runs/<run_id>/args.json` — the run
  form's payload, frozen at submit time. The worker's
  `training/config_build.py` maps `args` onto a `pdomain-ocr-training`
  `DetectionConfig` / `RecognitionConfig`
  ([`02-backend.md`](02-backend.md) §4.3).

### 3.2 Args schema per task

`Run.args` is the run-form payload. Detection `args` is structurally
the `pdomain-ocr-training` `DetectionConfig` tunable subset; recognition
`args` is the `RecognitionConfig` subset **except** the single
`vocab: str` field is presented as the two form fields
`vocab_library` + `custom_characters`, which `config_build` collapses
into `vocab`. Three config fields are **not** in `args` — `config_
build` injects them: `name` (← `CreateRunRequest.model_name` /
derived, [`06-training-runs.md`](06-training-runs.md) §6), `device`
(← `CreateRunRequest.device`), and `output_dir` (← the run's model
output path).

Seed defaults match the `pdomain-ocr-training` config-model defaults
exactly (`protocols.py:85-188`).

**Detection** (`DetectionConfig`):

```json
{
  "arch": "db_resnet50",
  "epochs": 100,
  "batch_size": 2,
  "workers": 4,
  "lr": 0.002,
  "weight_decay": 0.0,
  "optimizer": "adam",
  "scheduler": "poly",
  "input_size": 1024,
  "rotation": false,
  "amp": false,
  "pretrained": true,
  "early_stop": false,
  "early_stop_epochs": 5,
  "early_stop_delta": 0.01
}
```

**Recognition** (`RecognitionConfig`; note `epochs` default `10`,
not the legacy `100`, and the `vocab` substitution):

```json
{
  "arch": "crnn_vgg16_bn",
  "epochs": 10,
  "batch_size": 64,
  "workers": 4,
  "lr": 0.001,
  "weight_decay": 0.0,
  "optimizer": "adam",
  "scheduler": "cosine",
  "input_size": 32,
  "amp": false,
  "pretrained": true,
  "early_stop": false,
  "early_stop_epochs": 5,
  "early_stop_delta": 0.01,
  "vocab_library": ["french"],
  "custom_characters": "..."
}
```

**Typeface classification** (new task; the config model is a future
`pdomain-ocr-training` addition — [Q9](../OPEN_QUESTIONS.md)):

```json
{
  "arch": "<TBD>",
  "epochs": 50,
  "batch_size": 128,
  "workers": 4,
  "lr": 0.001,
  "input_size": 64,
  "amp": true
}
```

**Glyph classification** (new task; future `pdomain-ocr-training`
addition — [Q10](../OPEN_QUESTIONS.md)):

```json
{
  "arch": "<TBD>",
  "epochs": 50,
  "batch_size": 128,
  "workers": 4,
  "lr": 0.001,
  "input_size": 48,
  "amp": true,
  "feature_heads": ["ligature_ct", "ligature_st", "long_s", "swash"]
}
```

There is no `model_name_template` arg — the model name is derived
per [`06-training-runs.md`](06-training-runs.md) §6 (D-T6).

### 3.3 Endpoint surface

```
GET    /api/profiles/{name}/training-defaults/{task}   → defaults dict (404 → never edited; SPA falls back to seed)
PUT    /api/profiles/{name}/training-defaults/{task}   → 200, persisted
DELETE /api/profiles/{name}/training-defaults/{task}   → 204, falls back to seed
```

When `training_defaults.json` is absent, the seed is the
`pdomain-ocr-training` config-model default set (§3.2). A test asserts the
seed values field-for-field against `protocols.py`.

### 3.4 GPU / batch-size auto-suggest

```
GET /api/runtime/suggest-batch-size?task=detection|recognition
→ { "vram_gb": 24.0, "suggested_batch_size": 16 }
```

Picks a power-of-2 batch size from available VRAM. Device discovery
goes through `pdomain-ocr-ops` (`pdomain_ocr_ops.gpu.pick_device` and
friends) rather than a SPA-local CUDA probe. No GPU →
`vram_gb: 0`, `suggested_batch_size: 1`. The frontend offers the
value as a one-click "Use suggested" on the batch-size field.

### 3.5 Device selection

```
GET /api/runtime/devices
→ { "cuda": ["cuda:0", "cuda:1"], "mps": false, "cpu": true }
```

The run form lets the user pin a device or leave it on `auto`. A
pinned device becomes `CreateRunRequest.device` (a GPU index — the
`pdomain-ocr-training` config `device` field is `int | None`); `auto`
sends `device=None` and the worker resolves the default device at
start.

---

## 4. profile.toml format

Referenced from [`01-data-models.md`](01-data-models.md) §1.2.

```toml
# <ml_training_dir>/<profile>/profile.toml
display_name = "Cló Gaelach"          # optional
language = "ga"                       # optional, BCP-47
typeface = "clogaelach"               # optional, TypefaceEnum value
notes = "Imported from PGDP batch 3"  # optional, free-form
```

Reader: `tomllib`. Writer: a tiny custom function emitting exactly
these keys in stable order (no TOML-writer dependency). Unknown keys
are preserved verbatim on round-trip, serialized at file end.
Training-side and validation-side files are kept in sync (D-T5).

---

## 5. UI surface

Built on `pdomain-ui` (D-T19) — `AppShell`, `Card`, `Field`/`FieldRow`,
`Select`, `Button`. Profile data is held in a SPA **profiles store**
(a `pdomain-ui` store factory instance) feeding the table and dialogs;
mutations invalidate `["profiles"]` / `["profile", name]`.

`ProfilesPage` (route `/profiles`):

- `pdomain-ui` table — columns: name | display_name | language | typeface
  | detection / recognition / typeface / glyph counts | actions.
- "New profile" `Button` opens `ProfileEditDialog` in create mode.
- Each row clickable → `/profiles/{name}`.
- Row "..." menu: Edit, Delete (disabled if `is_base`), Migrate
  Legacy (visible only when a legacy flat layout is detected).

`ProfileDetailPage` (route `/profiles/{name}`):

- Header: profile name + language + typeface + edit affordance.
- Tabs: Datasets | Runs | Models.
- Datasets tab embeds the kanban for the default task (recognition).

`ProfileEditDialog`:

- `pdomain-ui` `FieldRow`s: display_name (text `Field`), language
  (`Select` / combobox with BCP-47 hints), typeface (`pdomain-ui Select`
  over `TypefaceEnum` minus `typeface`), notes (textarea `Field`).
- On submit: PATCH (or POST in create mode), then invalidate the
  profiles store queries.

---

## 6. Acceptance behaviour

1. Fresh install boots, hits `/api/profiles`, shows exactly one row:
   `all`, all counts zero.
2. Drop a labeler export under the export root; `POST
   /api/profiles/all/datasets/recognition/scan` shows the project in
   the Unassigned column.
3. Create profile `clogaelach` with `language=ga,
   typeface=clogaelach`; both `profile.toml` files exist with
   matching content.
4. PATCH `clogaelach` to clear typeface — files retain language
   only; PATCH again to clear language — both files deleted.
5. Save recognition training-defaults for `clogaelach` with
   `epochs: 50`; reopen the run form — epochs prefills `50` (an
   untouched form prefills the seed `10`).
6. Delete `clogaelach`; the dataset dirs go away,
   `<shared_models_dir>/` contents untouched.

---

## 7. Citations

- Profile constants / discovery / `BASE_OCR_PROFILE` / legacy
  migration: `pdomain-ocr-training/pdomain_ocr_training/datasets.py:19-86, 242-609`.
- `DetectionConfig` / `RecognitionConfig` canonical defaults:
  `pdomain-ocr-training/pdomain_ocr_training/protocols.py:85-188`.
- Custom-characters seed: `pdomain_book_tools.ocr.doctr_support.DEFAULT_CUSTOM_CHARACTERS`.
- GPU device selection: `pdomain-ocr-ops/pdomain_ocr_ops/gpu` (`pick_device`).
- Historical origin of the config knobs (legacy, repo being
  retired): `pdomain-ocr-training/src/pdomain_ocr_training/ui.py:74-318`.
