---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-12
Kind: plan
---

# Remaining work, in read order

## Agent Index

- **Kind:** plan
- **Status:** active
- **Read when:** deciding what to work on next in `pdomain-ocr-trainer-spa`.
- **Search terms:** roadmap, typeface, glyph eval, publish worker, jobs dock,
  device index

This file is the only backlog.

Shipped behavior is the architecture set.

Issue files keep the evidence for the four open product gaps.

Those files are not a second list.

## Goal

The work still open is in the order to read it.

### Typeface training, production eval, and the glyph classifier

#### Typeface training still calls `LocalTrainingRunner`

Production typeface training builds the local `TypefaceConfig` in
`training/config_build.py`. It calls `train_typeface` on a cast of
`LocalTrainingRunner`.

The call still uses that runner. The Protocol declares `train_detection` and
`train_recognition` only.

`FakeTrainingRunner` covers tests.

The field list is the local `TypefaceConfig` class. That class reads
`<profile>/typeface-classification/`.

The [M12 plan](plans/2026-06-10-m12-typeface-classifier.md) still shows
`<profile>/typeface/`. That path is stale.

The plan's cross-repo gate still lists those methods for
`pdomain-ocr-training`. That package's `docs/ROADMAP.md`, under "Keep out
of this package", says a typeface or glyph classifier stays out until the
owner confirms the scope. If it is built, it is a separate model package.
That package would add a runner contract only after the scope is confirmed.
This SPA would orchestrate it. Do not start that package now.

See the [M12 issue](issues/2026-07-21-gh-014-m12-typeface-classifier.md).

#### The eval worker never calls `LocalEvalRunner`

The production eval worker raises `RuntimeError` in `_build_runner`. It never
calls `LocalEvalRunner`.

The text inside the raise is stale. It says `RecognitionEvalConfig` lacks
glyph input. It also says recognition eval hard-codes `slices=[]`.

Installed `pdomain-ocr-training` 0.2.1 already has `glyph_annotations_path`
and `slice_glyph_features`. `evaluate_recognition_impl` fills slices when both
are set.

The eval form already shows a glyph-slice control.

See the [M13 issue](issues/2026-07-21-gh-015-m13-glyph-eval-slicing.md).

Slicing math stays in `pdomain-ocr-training`.

Acceptance here is:

- A recognition eval with slicing writes `slices[]` for every feature that has
  at least one labelled word.
- The table sorts by absolute CER delta.
- Rows with fewer than 30 positive samples are marked low support.

#### Kanban, training defaults, and `create_run` reject the glyph classifier

- Glyph-classifier kanban returns HTTP 501 `dataset.task_unsupported`.
- Training defaults return 422 `training_defaults.task_unsupported`.
- `create_run` returns 422 `run.task_unsupported`.

The same keep-out applies to the glyph classifier. This repo does not depend
on `pdomain-ocr-synth`.

`GlyphAnnotations` already exists in `pdomain-book-contracts`.

See the [M14 issue](issues/2026-07-21-gh-016-m14-glyph-classifier.md).

#### Umbrella stays open until those three close

The M0–M14 umbrella stays open until those three close.

See the [Umbrella issue](issues/2026-07-21-gh-001-milestone-roadmap.md).

### Open in this repository

#### Typeface apply writes a file the board does not read

Typeface kanban and `TypefaceConfig` read `metadata.jsonl`.

Apply writes `labels.json` for every task, including typeface, so an applied
move does not reload into the file training reads.

A partial apply is HTTP 200 with the header `X-Apply-Errors`. A fully failed
apply is 409 `dataset.apply_failed`.

#### `/publish` is not a working upload

The `/publish` page is not a working upload. Publish routes check the token
and the license, then `domain/publish.py` raises `AdapterNotImplementedError`.

The filesystem registry's `publish` method raises as well.

`HuggingFaceHubModelRegistry` raises on every call.

#### Terminal toasts do not fire

Terminal toasts do not fire.

`useNotificationStream` is tested and not mounted. `App.tsx` never calls
`emitToast`.

The jobs dock polls `GET /api/jobs` every 5 seconds.

Run detail opens the job SSE stream.

Do not add a third progress surface. Either mount the existing hook or delete
it.

See the [Jobs issue](issues/2026-07-21-gh-025-unify-jobs-surfaces.md).

#### Dock rows open the job id, not `run_id`

The row id is the job id, not `run_id`. Opening a dock row navigates to
`/runs/` plus the row id.

The dock copies `progress` into `pct`. `progress` is 0–1.

pdomain-ui `JobRow` treats `pct` as 0–100.

`cancelled` is sent as `failed`.

`pausable` is omitted, so Pause and Resume still show. The dock passes no
pause handler.

#### Banner links are not routes

The missing-token banner links to `/settings`, which is not a route. The
fresh-labeled-pages banner links to `/datasets`, which is not a route.

Settings in this app are a Compute panel on the utility dock, added after
Appearance.

A broken href is not a reason to build a settings page or a `/datasets` index.

#### `NewRunPage` does not send `device`

`NewRunPage` does not send `device`. The suite stores a device string.
`CreateRunRequest.device` is an optional integer.

The worker sets `CUDA_VISIBLE_DEVICES` only for an integer already on the
manifest. Do not invent the mapping.

See the [Review-fixes plan](plans/2026-07-14-review-fixes.md).

#### Env flags are emitted and unread

No React module reads the flags `/env.js` emits. The flags are
`enableTypefaceTraining`, `enableGlyphTraining`, and `enableHfPublish`.

Publish routes do not read `enable_hf_publish` either.

#### `just openapi-export` is not a gate

`just openapi-export` calls `pdomain_ocr_trainer_spa.scripts.export_openapi`.
That module is not in the tree.

There is no generated TypeScript client.

Do not treat the target as a gate.

### Deferred until there is a concrete need

- Revisit the 50,000-event `progress.jsonl` cap only if a real run reaches it.
- Add a regression webhook only when a consumer and an endpoint exist.
- Decide HF default owner, source-weight retention, and LFS quota errors only
  when publish itself works.
- Persist job event history, or supervise a detached worker, only if losing
  history or long runs shows up in use.
- Keep banner dismissal per tab unless re-dismissing the same banner becomes
  a repeated complaint.
- Add `Ctrl+K` navigation only when the rail is not enough.
- Add a deep link that opens an export in the labeler only after the labeler
  owns a stable project and page URL.
- Replace the manifest bridge with PageRecord only when both apps can share
  identity without app-specific behavior.
  [Labeler import](architecture/labeler-import-and-freshness.md).
- Add MPS guidance only after measurement shows a useful warning.
- Consider a headless `pdomain-ocr-trainer-spa-driver` only after a CI
  pre-pass must create profiles, import a known export, start training, wait,
  and archive results. Until that need is real, the inventory stays in
  [specs/13-driver-contract.md](../specs/13-driver-contract.md), because
  `tests/e2e/test_driver_contract.py` parses that file. Do not build the
  driver repo now.
- Consider a separate model package for a typeface or glyph classifier only
  after the owner confirms the scope. `pdomain-ocr-training` `docs/ROADMAP.md`
  keeps that classifier out of that package. If it is built, it is a separate
  model package, and that package would add a runner contract only after the
  scope is confirmed. This SPA would orchestrate it. Do not start the package
  now.

### Dropped from the old root specs

They are not backlog.

These were specified and never built.

The specs that listed them are superseded.

- A `/settings` page, `GET /api/settings`, a vocab library endpoint, and
  missing-character scan.
- `GET /api/runtime/devices`, batch-size suggestion, and an ndjson run log.
  Run progress is `GET /api/runs/{run_id}/progress` as JSON.
- A source-list route. The only source route is
  `GET /api/sources/huggingface/preview`.
- S3 storage. `S3Storage` raises `AdapterNotImplementedError` on use.
- Recharts, `react-hotkeys-hook`, a generated OpenAPI client, MSW browser
  tests, and GitHub Actions workflows. Charts are local SVG. Release is
  `scripts/do-release.sh`. Chords such as `g p` stay unregistered.

## Architecture

These pages are the shipped behavior.

- [Trainer workflows](architecture/trainer-workflows.md)
- [Profiles, datasets, and models](architecture/profiles-datasets-and-models.md)
- [Runs and evaluation](architecture/runs-and-evaluation.md)
- [Shell, jobs, and the client contract](architecture/shell-and-jobs.md)
- [Hugging Face read and publish](architecture/huggingface.md)
- [Labeler import and freshness](architecture/labeler-import-and-freshness.md)

Commands and the wheel are in [DEVELOPMENT.md](../DEVELOPMENT.md).

## Tech Stack

The stack is Python with FastAPI and a React 19 TypeScript SPA on
`@pdomain/pdomain-ui`.

- Long jobs use `pdomain-ops`.
- Detection and recognition training call `pdomain-ocr-training`.
- License ids for publish checks come from `pdomain-book-tools`.

The web process does not import torch.

Bootstrap stores `NoneAuth`.

No request handler calls `current_user`.

## Global Constraints

- Do not treat seam tests as proof of production typeface training, production
  eval, or Hugging Face upload.
- Do not add a third job-progress surface. The live surfaces are the polling
  dock and the run-detail SSE stream.
- Do not invent the run-form device mapping before an owner decides it.
- Do not recreate `.github/workflows` or a generated client from the old
  specs.
- Do not start a driver repository until the deferred CI condition is real.
- Do not start a classifier package until the owner confirms the scope in
  the deferred list. Glyph-annotation slices stay in `pdomain-ocr-training`.
  Do not put the classifier in `pdomain-ocr-synth`.

## Work that belongs in other repositories

Build the rows that already have an owner in that sibling. The classifier
row is a new package only after the owner confirms the scope.

| Work | Where it belongs | Why |
| --- | --- | --- |
| Typeface or glyph classifier model | A separate model package, after the owner confirms the scope | `pdomain-ocr-training` `docs/ROADMAP.md` keeps that classifier out. The SPA today calls `train_typeface` on a cast of `LocalTrainingRunner`. The field list is the local class in `training/config_build.py`. The M12 plan path `<profile>/typeface/` is stale. Local code uses `typeface-classification`. This repo rejects glyph kanban with HTTP 501 `dataset.task_unsupported`, training defaults with 422 `training_defaults.task_unsupported`, and `create_run` with 422 `run.task_unsupported`. Do not start the package now. Do not put it in `pdomain-ocr-synth`. |
| Glyph-annotation slices and `LocalEvalRunner` | `pdomain-ocr-training` | Version 0.2.1 already has `glyph_annotations_path` and `slice_glyph_features` on `RecognitionEvalConfig`. This repo's worker still raises in `_build_runner`. |
| `LongJobRunner`, suite device, `mount_routes` | `pdomain-ops` | This app already mounts them. |
| Shared shell and shortcut help | `pdomain-ui` | The SPA renders the local `KanbanBoard.tsx` even though the package exports a board. `LogViewer` stays local. |
| Labeler export manifest | `pdomain-ops` | The trainer reads it through `pdomain_ops.schemas.doctr_export`. This repo does not depend on the labeler repository. |

Corpus backfill onto Hugging Face, from the old deferred HF note, is not an
application repo and not SPA work. It is an operations task over data.

`GlyphAnnotations` already lives in `pdomain-book-contracts`.

PageRecord exchange stays on the deferred list.

## Issue files for this backlog

- [M0–M14 umbrella](issues/2026-07-21-gh-001-milestone-roadmap.md)
- [M12 typeface classifier](issues/2026-07-21-gh-014-m12-typeface-classifier.md)
- [M13 glyph eval slicing](issues/2026-07-21-gh-015-m13-glyph-eval-slicing.md)
- [M14 glyph classifier](issues/2026-07-21-gh-016-m14-glyph-classifier.md)
- [Jobs surfaces](issues/2026-07-21-gh-025-unify-jobs-surfaces.md)
