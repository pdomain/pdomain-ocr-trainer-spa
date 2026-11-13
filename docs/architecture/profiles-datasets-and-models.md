---
Status: active
Owner: CT
Created: 2026-11-12
Last verified: 2026-11-13
Kind: architecture
---

# Profiles, datasets, and models

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** changing profiles, the dataset kanban, or the model registry.
- **Search terms:** profile.toml, kanban, shared-models, sidecar, typeface
  dataset, glyph kanban

Profiles, dataset assignment, and the model registry live as files on disk. The
web process reads and writes those files. It does not import torch.

## Where profile names come from

Training and validation roots come from `PD_OCR_TRAINER_SPA_ML_TRAINING_DIR`
and `PD_OCR_TRAINER_SPA_ML_VALIDATION_DIR`. The defaults are `~/ml-training`
and `~/ml-validation`.

`_discover_names` always includes `all`. It also adds child directories of
the training root, the validation root, `shared_models_dir`, and an existing
`labeler_export_root`.

`normalize_profile_name` lowercases the name and turns spaces and underscores
into hyphens. It maps `base-ocr` or an empty name to `all`.

## Profile.toml keys and conflicts

Each profile may have a `profile.toml` in the training directory and another
in the validation directory. Known keys are `display_name`, `language`,
`typeface`, and `notes`.

A conflict is 409 `profile.toml.conflict` only when both parsed dictionaries
are nonempty and differ. A missing or empty file does not conflict with a
populated one.

`GET /api/profiles` loads every discovered profile, so one conflict fails the
whole list.

## What blocks deleting a profile

`all` cannot be deleted. The attempt returns HTTP 409 `profile.is_base`.

Delete also returns 409 `profile.has_data` when
`<train|val>/<profile>/{detection,recognition,typeface,glyph}/` holds
`labels.json` or `metadata.jsonl`. It returns 409 `profile.has_data` when
`<shared_models_dir>/<name>/` is not empty.

Files under `typeface-classification/` alone do not block delete. An accepted
delete removes the profile directory recursively.

Profile summaries count classifier data under `typeface/` and `glyph/`, while
the typeface workflow uses `typeface-classification/`. The summary's has-data
flags cover detection and recognition only.

## How legacy layout is detected and moved

`has_legacy_layout` looks only at the training root, and only for flat
`detection` and `recognition` directories.

`POST /api/profiles/migrate-legacy` walks both training and validation roots.
It moves a flat `detection` or `recognition` directory under `all/`. It skips
that task when `all/<task>` already exists. The route returns 204 even when
nothing moved.

## Training defaults for detection and recognition

Training defaults for detection and recognition are a JSON file at
`<app_data_root>/profiles/<name>/training_defaults.json`. The routes are
`/api/profiles/{name}/training-defaults/{task}`.

Seeding typeface or glyph defaults returns 422
`training_defaults.task_unsupported`.

The profile page edits detection and recognition defaults only.

## How the dataset kanban loads and saves

Supported kanban tasks are detection, recognition, and
typeface-classification. Columns are `unassigned`, `train`, and `val`.

- The board loads with `GET .../datasets/{task}/kanban`.
- The browser stages moves in `datasetsStore.ts`.
- Apply posts the diff to `POST .../datasets/{task}/apply`.
- Scan is `POST .../datasets/{task}/scan`.
- Include toggles are `POST .../datasets/{task}/include-toggles`.

An applied typeface move does not reload from the file the board reads.

Typeface and glyph reads use `metadata.jsonl` in `_read_task_labels`.

Apply writes `labels.json` for every task in `_write_labels`.

## Which UI components stay local

The page renders the local file
`frontend/src/components/kanban/KanbanBoard.tsx`. `@pdomain/pdomain-ui` also
exports `KanbanBoard`. This app does not import that export.

`LogViewer` stays local. `LossChart` is the local SVG chart.

## Why glyph kanban and glyph training are rejected

Glyph kanban raises `dataset.task_unsupported`, HTTP 501.
`test_glyph_classifier_task_still_rejected` locks that status.

Glyph training is a separate rejection. `create_run` returns 422
`run.task_unsupported`.

## Dataset page routes and the typeface path

The typeface board has its own page at
`/profiles/:name/datasets/typeface-classification`. Detection and recognition
use `/profiles/:name/datasets/:task`.

The local `TypefaceConfig` reads `<profile>/typeface-classification/`. The M12
plan's `<profile>/typeface/` path is stale.

## Where labeler discovery and freshness are documented

Labeler export discovery and freshness are in
[labeler import and freshness](labeler-import-and-freshness.md).

## Where shared model files live

Models live under `shared_models_dir`. The default is `~/shared-models` unless
`PD_OCR_TRAINER_SPA_SHARED_MODELS_DIR` is set.

Discovery walks `<shared_models_dir>/<profile>/<task>/<name>/`. The leaf
directory counts as a model when it holds a `.pt`, `.safetensors`, or `.bin`
file, or a `*.metadata.json` sidecar alone.

Loose files in the models root are not models.

Sidecars are read, written, and regenerated in that leaf.

## How model names are built and parsed

`derive_model_name` builds the name `pd-{language}-{typeface}-{task}-{date}`
and appends an optional qualifier.

The parser regex has no date group. It accepts `pd-` plus a language of
`[a-z]{2,3}`, a typeface, and a task. Everything after the task, including
the date, is the qualifier.

A language outside that pattern parses as legacy, including a name this app
built.

Legacy names stay readable.

Publish returns 422 `publish.legacy_name` only after `get_model` finds the
model on disk. An unknown name is 404 `model.unknown` first.

Eval loads any known model and does not apply the legacy check.

## Model routes and the registry publish method

`/api/models` lists, scans, reads, patches, deletes, renames, and regenerates
sidecars. The pages are `/models` and `/models/:name`.

The filesystem registry `publish` method raises `AdapterNotImplementedError`.

## Code paths and tests read on 2026-11-12

- Code: `src/pdomain_ocr_trainer_spa/domain/profiles.py`,
  `src/pdomain_ocr_trainer_spa/domain/datasets.py`,
  `src/pdomain_ocr_trainer_spa/domain/models.py`,
  `src/pdomain_ocr_trainer_spa/domain/runs.py`,
  `src/pdomain_ocr_trainer_spa/training/config_build.py`,
  `src/pdomain_ocr_trainer_spa/api/profiles.py`,
  `src/pdomain_ocr_trainer_spa/api/datasets.py`,
  `src/pdomain_ocr_trainer_spa/api/models.py`,
  `src/pdomain_ocr_trainer_spa/settings.py`,
  `frontend/src/stores/datasetsStore.ts`,
  `frontend/src/App.tsx`
- Tests: `tests/unit/domain/test_datasets.py`
  (`test_glyph_classifier_task_still_rejected`),
  `tests/integration/api/test_datasets.py`
- Verified: 2026-11-12 by reading those files. Tests were not rerun.
