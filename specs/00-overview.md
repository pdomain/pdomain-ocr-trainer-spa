# 00 — Overview

`pd-ocr-trainer-spa` reimplements the existing `pd-ocr-trainer` (NiceGUI
training/dataset UI) as a **FastAPI + React/Vite/TypeScript SPA**,
structurally modelled on `pd-ocr-labeler-spa` and (further upstream)
`pd-prep-for-pgdp`.

This document is the entry point for every other spec. Read it once,
then jump to the per-area spec for whatever you're implementing.

---

## Goals

1. **Functional parity** with the current trainer. Every interactive
   capability of `pd-ocr-trainer/src/pd_ocr_trainer/ui.py` and
   `dataset_ui.py` (profile management, OCR config, dataset kanban,
   detection/recognition training, model export, model name prefix)
   must work end-to-end against the same on-disk artefacts under
   `ml-training/<profile>/...`, `ml-validation/<profile>/...`,
   `matched-ocr/`, `dist/`.
2. **Forward parity** with the trainer ROADMAP. The SPA must support
   typeface-classifier training (milestone (a.5) in
   `pd-ocr-trainer/docs/ROADMAP.md`), glyph-feature classifier (g2),
   eval slicing (g1), and HF dataset publish/read paths (a)/(b)/(c)
   without architectural rework — these are first-class adapters and
   pages from M0.
3. **Typed REST + SSE surface.** Every UI action has a documented
   FastAPI endpoint; the SPA consumes it via a generated TS client.
   See [`02-backend.md`](02-backend.md).
4. **Single-wheel distribution.** End users install with
   `uv tool install pd-ocr-trainer-spa` and get one binary
   (`pd-ocr-trainer-ui`) that serves both API and SPA.
   See [`15-deployment-dev.md`](15-deployment-dev.md).
5. **Milestone-implementable by AI agents.** Each milestone in
   [`16-milestones.md`](16-milestones.md) is bounded enough that a
   single coding agent can pick it up, deliver it, and verify against
   the listed acceptance tests.

## Non-goals

- **No replacement for the legacy trainer until parity ships.** Both
  binaries must coexist on the same machine and on the same
  `ml-training/` tree. Disk format does not change.
- **No new training algorithms.** Detection / recognition / typeface /
  glyph training entry points stay in `pd_ocr_trainer.train_*`
  modules (or a `pd-ocr-trainer-core` package extracted from them);
  the SPA only invokes them via the `ITrainingRunner` adapter.
  See [`02-backend.md`](02-backend.md) §Adapters.
- **No NiceGUI / Quasar.** Drop the entire NiceGUI stack; UI is React,
  styling Tailwind + shadcn/ui. ([D-004](17-decisions.md))
- **No multi-user collaboration.** One user, possibly multiple browser
  tabs against the same backend, sharing in-memory state.
  ([D-023](17-decisions.md))
- **No new on-disk dataset format.** Detection parquet, recognition
  imagefolder, `labels.json`, `metadata.jsonl` are byte-for-byte
  preserved per `pd-ocr-trainer/docs/DATASETS.md`.
- **No public REST contract.** The API is intentionally unstable
  across SPA versions. Internal use only — the SPA frontend is the
  only known consumer in v1.
- **No model-training-from-scratch UI work.** Hyperparameter sweeps,
  curriculum design, and architecture choice remain CLI / notebook
  workflows; the SPA exposes the existing knobs from the legacy
  trainer (epochs, batch size, vocab, augmentation toggles, …) and
  nothing more.

## Tech stack

### Backend

| Layer | Choice | Why |
|---|---|---|
| Web framework | **FastAPI** | Same as labeler-spa / pgdp-prep. Pydantic v2, async, OpenAPI export. |
| Server | **uvicorn[standard]** | Same as labeler-spa. |
| Persistence | **Filesystem only** | Single user; profile state, run metadata, datasets all live on disk. |
| Storage adapter | **`IStorage` Protocol** with `filesystem` impl + `s3` `NotImplementedYet` stub | Mirrors labeler-spa. ([D-019](17-decisions.md)) |
| Auth | **`IAuth` Protocol**, `none` impl only | Same seam as labeler-spa. ([D-005](17-decisions.md)) |
| Training runner | **`ITrainingRunner` Protocol** + `local_subprocess` impl + `modal` / `shared_container` `NotImplementedYet` stubs | Wraps the existing `pd_ocr_trainer.train_detect.main` / `train_recog.main` / `train_typeface.main` / `train_glyph.main` entry points. ([D-T1](17-decisions.md)) |
| Dataset source | **`IDatasetSource` Protocol** + `local` + `huggingface` impls | Mirrors trainer ROADMAP milestone (a). ([D-T2](17-decisions.md)) |
| Model registry | **`IModelRegistry` Protocol** + `filesystem` (`dist/`) + `huggingface_hub` (`push_to_hf_hub`) impls | Trainer ROADMAP (b)/(d). |
| Long jobs | **In-process job runner**, SSE for progress | Same shape as labeler-spa `core/job_runner.py` but training jobs are typically *minutes to hours* — see [`10-jobs-and-sse.md`](10-jobs-and-sse.md) for restart-survival. ([D-T3](17-decisions.md)) |
| Logging | stdlib JSON + `RequestIdMiddleware` | Verbatim port from labeler-spa. |

### Frontend

| Layer | Choice | Why |
|---|---|---|
| Build | **Vite** | Same as labeler-spa. |
| Framework | **React 19** | Same as labeler-spa. |
| Lang | **TypeScript** strict | Same as labeler-spa. |
| Routing | **`react-router-dom` v7** | Same as labeler-spa. |
| Server state | **`@tanstack/react-query` v5** | Same as labeler-spa. |
| Local state | `useState` + `useReducer`; **`zustand`** for cross-page UI prefs (selected profile, kanban filters, log auto-scroll). | Same pattern as labeler-spa. |
| Styling | **Tailwind 3.4** + **shadcn/ui** | Same as labeler-spa. |
| DnD (kanban) | **`@dnd-kit/core`** + `@dnd-kit/sortable` | NiceGUI kanban uses raw HTML5 drag events; we replace with dnd-kit for a11y + keyboard support. ([D-T4](17-decisions.md), [Q1](../OPEN_QUESTIONS.md)) |
| Toasts | **`sonner`** | Same as labeler-spa. |
| Hotkeys | **`react-hotkeys-hook`** | Same as labeler-spa. |
| Charts (loss curves, eval) | **`recharts`** | Lightweight, dependency-light, plays well with React 19. ([Q2](../OPEN_QUESTIONS.md)) |
| Log viewer | **virtualized `<div>` list** (`@tanstack/react-virtual`) | Training emits thousands of stdout lines; can't render unvirtualized. |
| Forms | Controlled inputs + `useMutation` | Same as labeler-spa. |
| Testing (unit) | **Vitest** + **@testing-library/react** | Same as labeler-spa. |
| HTTP mocking | **msw** | Same as labeler-spa. |
| E2E | **Playwright** (Chromium) | Same as labeler-spa. |

### Tooling

| Tool | Notes |
|---|---|
| Python build | `hatchling` + `hatch-vcs`. |
| Wheel-with-SPA | `force-include = src/pd_ocr_trainer_spa/static` + `build_hooks/spa_check.py`. |
| Lockfile | `uv.lock`. |
| Lint | `ruff` (Python) + `eslint` flat config (TS). |
| Format | `ruff format` + `prettier`. |
| Type-check | TypeScript `strict` + `pyright`. |
| Pre-commit | Same hooks as labeler-spa. |
| CI | Single `release.yml`: lint → test → frontend-build → wheel-build (with SPA assertion) → on tag, attach wheel to GitHub Release + publish to `pd-index` (per workspace release strategy). |
| Versions | `mise.toml` pinning Node 24 + Python 3.13. |

---

## Architectural shape

```
┌──────────────────────────────────────────────────────────────┐
│  Browser (SPA)                                               │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────┐  │
│  │ Profiles   │ │ Datasets   │ │ Training   │ │ Models    │  │
│  │ + Config   │ │ Kanban     │ │ Runs + Log │ │ + Eval    │  │
│  └────────────┘ └────────────┘ └────────────┘ └───────────┘  │
│         │             │               │             │        │
│         └────────── react-query (server state) ─────┘        │
│                              │                               │
└──────────────────────────────┼───────────────────────────────┘
                               │ HTTP/JSON + SSE
┌──────────────────────────────┼───────────────────────────────┐
│  FastAPI (single process)                                    │
│  ┌──────────────────────┐  ┌────────────────────────────┐    │
│  │  /api/profiles/*     │  │  /api/runs/* (training)    │    │
│  │  /api/datasets/*     │  │  /api/jobs/{id}/events SSE │    │
│  │  /api/models/*       │  │  /api/eval/*               │    │
│  │  /api/sources/*      │  │  /api/publish/*            │    │
│  └──────────────────────┘  └────────────────────────────┘    │
│                              │                               │
│  ┌────────── core (in-memory) ────────────────────────┐      │
│  │  AppState ─ Profiles ─ Runs ─ Jobs                 │      │
│  └────────────────────────────────────────────────────┘      │
│                              │                               │
│  ┌─────── adapters ──────────────────────────────────┐       │
│  │  IStorage(filesystem)   IAuth(none)               │       │
│  │  ITrainingRunner(local_subprocess)                │       │
│  │  IDatasetSource(local | huggingface)              │       │
│  │  IModelRegistry(filesystem | huggingface_hub)     │       │
│  └───────────────────────────────────────────────────┘       │
│                              │                               │
└──────────────────────────────┼───────────────────────────────┘
                               │ Python imports
                ┌──────────────▼───────────────┐
                │  pd-ocr-trainer (or          │
                │  pd-ocr-trainer-core if we   │
                │  extract): train_detect,     │
                │  train_recog, train_typeface,│
                │  train_glyph, dataset_store  │
                └──────────────────────────────┘
                               │
                ┌──────────────▼───────────────┐
                │  pd-book-tools (Page, Block, │
                │   Word, BBox, GlyphAnnots)   │
                └──────────────────────────────┘
```

### Key design rules

1. **`build_app(settings)` factory.** Same as labeler-spa. Every test
   wires its own `Settings` explicitly. The `__main__` script reads
   env vars itself.
2. **In-memory state on `app.state`.** `AppState` lives there; routers
   pull it via `Depends(get_app_state)`. No global singleton.
3. **One state mutation per HTTP request.** Bulk operations (e.g.
   "move 30 selected pages from Unassigned to Training") land as
   single endpoints with batch payloads.
4. **Autosave is server-side.** The SPA calls a single mutation
   endpoint per user action; the server writes through to disk and
   any caches. No client-side autosave timer.
5. **OpenAPI is source of truth.** `make openapi-export` regenerates
   `frontend/src/api/types.ts`. CI gate: `git diff --exit-code` after
   re-running.
6. **`IStorage` keys are profile-scoped.** Same sandboxing primitive
   as labeler-spa.
7. **No backwards-compat shims.** New repo. We read and write the
   same disk layout the legacy trainer uses, but with no transient
   v0 envelopes to preserve.
8. **Driver-facing surface is part of the contract.** Every
   `data-testid` and URL shape lives in
   [`13-driver-contract.md`](13-driver-contract.md).
9. **Training entry points stay where they are.** The SPA imports and
   calls `pd_ocr_trainer.train_detect.main(args)` (and friends) via
   `ITrainingRunner.local_subprocess`, which spawns a subprocess so
   stdout/stderr can be captured line-by-line. No re-implementation
   of the training loops here. ([Q3](../OPEN_QUESTIONS.md) — extract
   to `pd-ocr-trainer-core` or import from `pd-ocr-trainer`?)

---

## State model

The legacy trainer has implicit state in `ui.py` module-level
variables and the on-disk `dataset_store.py` files:

- **Profiles** — `get_available_model_profiles()`,
  `MODEL_NAME_PREFIX`, `BASE_OCR_PROFILE`. Stored in
  `TRAINER_SETTINGS_PATH`. Migrated from legacy layout via
  `migrate_legacy_dataset_layout()`.
- **Datasets** — split between `ml-training/<profile>/...` and
  `ml-validation/<profile>/...`. Source pages live in
  `matched-ocr/`, get assigned to splits via the kanban.
- **Runs** — currently **not persisted**: training start/stop is
  in-memory threading; logs scroll into a `ui.log()` widget and are
  lost on tab close. The SPA fixes this — every run gets a
  `runs/<run_id>/` directory with stdout, stderr, args, status, and
  artefact paths.
- **Models** — `dist/` contains `.whl` for the trainer itself but
  trained model artefacts go to `model_output_dir(profile, task)`.
  The sidecar lives next to the artefact (see
  [`08-models.md`](08-models.md)).

In the SPA:

- Backend keeps a single `AppState` with profile registry, dataset
  index, run registry, job registry. All hydrated from disk on
  startup and refreshed on demand.
- Frontend keeps per-tab UI state (selected profile, kanban filter,
  selected run, log auto-scroll) in `useState` + `zustand`. Two tabs
  share document state on the server but each has independent UI.
- Long-running jobs are tracked on the server. SSE streams progress;
  reloading the SPA mid-run reattaches to the running job. ([D-T3](17-decisions.md))

---

## Dataflow per user action

The shape `(user action) → (HTTP/SSE) → (server logic) → (client refetch)`
applies uniformly. Examples:

### Drag a page chip from Unassigned → Training (kanban)

- SPA optimistically moves the chip in the cached query result.
- `POST /api/profiles/{profile}/datasets/move`
  with `{from: "unassigned", to: "train", page_keys: ["projID_42"]}`.
- Server: `ExportManager.move_pages(...)` (mirrors current
  `dataset_store.py` behaviour) → on-disk hardlinks/copies updated.
- Server returns the new kanban state for that profile.
- SPA reconciles cache.

### Start a recognition training run

- SPA calls `POST /api/runs` with `{profile, task: "recognition",
  args: {epochs, batch_size, vocab, ...}}`.
- Server creates a `runs/<run_id>/` dir, writes `args.json`, returns
  `202 Accepted` with `{run_id, job_id}`.
- SPA opens `EventSource(/api/jobs/{job_id}/events)` for stdout +
  progress events.
- Server's `JobRunner` spawns the training subprocess, parses
  progress, emits `progress(epoch, total_epochs, message)` and
  `log(stream, line)` events. Terminal `complete` or `failed` event
  with exit code.
- On terminal: SPA invalidates the run-detail query; refetch shows
  final status, artefact paths, sidecar.

### Publish a dataset to Hugging Face

- Same shape as Refine in labeler-spa: `POST /api/publish/dataset`
  → 202 + `job_id`. Server runs `huggingface_hub.HfApi.upload_large_folder`,
  emits per-file progress, terminal event with the resulting repo
  revision.

---

## Milestone contract for AI agents

Every milestone in [`16-milestones.md`](16-milestones.md) follows the
same format used in `pd-ocr-labeler-spa`:

```
## Mn — short title

**Outcome.** One paragraph describing what works at end of milestone.
**Files to create / modify.** Listed.
**Specs that govern this milestone.** Listed.
**Acceptance tests.** pytest / vitest / playwright cases.
**Rollback.** What's not isolated to the listed files.
**Pre-conditions.** What earlier milestones must already exist.
```

The spec author's bet is that an AI agent given just (a) the listed
spec files, (b) the listed acceptance tests, and (c) the previous
milestone's working state can deliver the milestone in a single
coding session. If a milestone is too big, split it.

---

## Running spec list (must read before coding)

| If you're touching… | Required reading |
|---|---|
| Anything | `00-overview.md`, `OPEN_QUESTIONS.md` |
| Backend route | `01-data-models.md`, `02-backend.md` |
| New page in SPA | `03-frontend.md`, `13-driver-contract.md` |
| Profile / OCR config | `04-profiles-and-config.md` |
| Dataset kanban | `05-dataset-kanban.md`, `12-hotkeys-a11y.md` |
| Training | `06-training-runs.md`, `10-jobs-and-sse.md` |
| Eval | `07-evaluation-and-metrics.md` |
| Model export / publish | `08-models.md`, `09-hf-integration.md` |
| Notifications | `11-notifications.md` |
| Tests | `14-testing.md` |
| Build / install | `15-deployment-dev.md` |
| Roadmap | `16-milestones.md` |

If a question isn't answered by the linked spec, **stop and add it to
[`OPEN_QUESTIONS.md`](../OPEN_QUESTIONS.md)** rather than guessing.
