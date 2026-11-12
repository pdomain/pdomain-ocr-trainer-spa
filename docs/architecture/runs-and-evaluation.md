---
Status: active
Owner: CT
Created: 2026-11-12
Last verified: 2026-11-12
Kind: architecture
---

# Runs and evaluation

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** changing training runs, the eval worker, or run pages.
- **Search terms:** LocalTrainingRunner, TypefaceConfig, evaluate, NewRunPage,
  run.already_running

Training and evaluation create run records and hand the work to a worker
subprocess.

The web process stays free of torch.

- Detection and recognition training call `LocalTrainingRunner`.
- Typeface training calls `train_typeface` on a cast of that runner.
- Production eval raises before it builds a runner.

## Run records and the second-run rejection

`POST /api/runs` returns 202 and a run id.

Run files live under `runs_dir`, which defaults to the app-data `runs`
directory.

The API also lists a run, reads it, cancels it, deletes it, and reads
`progress.jsonl`.

A second training submission while any tracked run is `pending` or `running`
returns 409 `run.already_running`.

Extra training runs are not queued.

## Run pages and the device field

Pages are `/runs`, `/runs/new`, and `/runs/:runId`.

The new-run form does not send `device`.

The worker sets `CUDA_VISIBLE_DEVICES` only when the run manifest already
contains an integer `device`.

The string stored by the suite device control is a different value. That
mapping is undecided. See the [roadmap](../roadmap.md).

## Detection and recognition training

`worker/train.py` builds `LocalTrainingRunner` from `pdomain-ocr-training`.

The worker's declared type has `train_detection` and `train_recognition`.

Config objects are built in `training/config_build.py` from the run args.

Tests can inject `FakeTrainingRunner`, which scripts events for detection,
recognition, and typeface.

That fake is not the production runner.

## Typeface training

The typeface dataset kanban and the run form exist.

For task `typeface-classification`, `worker/train.py` builds the local
`TypefaceConfig` in `training/config_build.py`. It calls `train_typeface`
on a cast of the runner.

The call still goes through `LocalTrainingRunner` and does not skip that
runner.

The Protocol the worker declares has `train_detection` and
`train_recognition` only.

The local class reads `<ml_training_dir>/<profile>/typeface-classification/`.

Its fields are `train_path`, `val_path`, `arch`, `epochs`, `batch_size`,
`lr`, `weight_decay`, `optimizer`, `scheduler`, `input_size`, and
`num_classes`. They also include `workers`, `amp`, `early_stop`,
`early_stop_epochs`, `early_stop_delta`, `output_dir`, `device`,
`pretrained`, and `name`.

The [M12 plan](../plans/2026-06-10-m12-typeface-classifier.md) still shows
`<profile>/typeface/`. That path is stale.

Use this class as the field list. The plan's cross-repo gate still names
those methods for `pdomain-ocr-training`. That package's `docs/ROADMAP.md`
keeps a typeface or glyph classifier out until the owner confirms the scope.
If it is built, it is a separate model package.

`enable_typeface_training` defaults to true.

It is copied onto `/env.js`.

The React app does not read it.

The flag does not select the worker branch.

## Eval routes and the result page

`POST /api/eval` creates an eval run.

Result routes are `GET /api/eval/{run_id}/result` and
`GET /api/eval/{run_id}/result.md`.

The form at `/eval` includes a glyph-annotation slice control.

The result page is `/eval/:runId/result`.

It renders `result.slices`.

It does not read query parameters.

## Why the production worker does not score

The production worker does not score a model.

In `worker/evaluate.py`, `_build_runner` raises `RuntimeError` and never
calls `LocalEvalRunner`.

The text inside that raise is stale against installed
`pdomain-ocr-training` 0.2.1. It says `RecognitionEvalConfig` has no glyph
input and that recognition eval hard-codes `slices=[]`.

`RecognitionEvalConfig` in that package has
`glyph_annotations_path: Path | None = None` and
`slice_glyph_features: bool = False`.

`evaluate_recognition_impl` fills slices when both are set.

The `slices=[]` assignment in `_eval_backend.py` is the detection path.

`test_build_runner_surfaces_upstream_gap` calls `_build_runner` and expects
the `RuntimeError`.

The round-trip test injects a stub and does not call `_build_runner`.

## Glyph gates and the acceptance still open

Glyph kanban, glyph training, and this raise are separate gates.

- Kanban is HTTP 501 `dataset.task_unsupported`.
- `create_run` is 422 `run.task_unsupported`.

See [profiles, datasets, and models](profiles-datasets-and-models.md).

`GlyphAnnotations` already exists in `pdomain-book-contracts`, at
`pdomain_book_contracts.ocr.glyph_annotations`.

The comment at the top of `worker/evaluate.py` still names
`pdomain-book-tools`.

Slicing math stays in `pdomain-ocr-training`.

The remaining acceptance is on the [roadmap](../roadmap.md):

- Every labelled feature writes `slices[]`.
- The table sorts by absolute CER delta.
- `n_pos` under 30 is low support.

## Code, tests, and the 2026-11-12 read

- Code: `src/pdomain_ocr_trainer_spa/worker/train.py`,
  `src/pdomain_ocr_trainer_spa/worker/evaluate.py`,
  `src/pdomain_ocr_trainer_spa/training/config_build.py`,
  `src/pdomain_ocr_trainer_spa/training/fake_runner.py`,
  `src/pdomain_ocr_trainer_spa/api/runs.py`,
  `src/pdomain_ocr_trainer_spa/api/eval.py`,
  `frontend/src/pages/NewRunPage.tsx`,
  `frontend/src/pages/EvalFormPage.tsx`
- Tests: `test_build_runner_surfaces_upstream_gap` in
  `tests/unit/worker/test_evaluate.py`,
  `test_iter_events_typeface_calls_train_typeface` in
  `tests/unit/training/test_worker_dispatch.py`, and
  `tests/e2e/test_m12_typeface.py`
- Verified: 2026-11-12 by reading those files and the installed
  `pdomain-ocr-training` 0.2.1: glyph fields in `protocols.py` and
  recognition slices in `_eval_backend.py`. Tests were not rerun.
