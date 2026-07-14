# 00 — Overview

`pdomain-ocr-trainer-spa` reimplements the existing `pdomain-ocr-training` (NiceGUI
training/dataset UI) as a **FastAPI + React/Vite/TypeScript SPA**, built on
the workspace-standard **`pdomain-ui` + `pdomain-ocr-ops` + `pdomain-ocr-training`** stack
and structurally modelled on the shipped `pdomain-ocr-labeler-spa`.

This document is the entry point for every other spec. Read it once,
then jump to the per-area spec for whatever you're implementing.

> **Re-spec note.** This overview supersedes the original `00`/`17` specs,
> which predated the workspace decision to standardize SPAs on `pdomain-ui` +
> `pdomain-ocr-ops`. The old specs rejected `pdomain-ui` (shadcn/ui + Tailwind) and
> assumed the legacy trainer kept existing (training driven by subprocess
> calls into `pdomain_ocr_training.train_*`). Both assumptions are gone. See the
> cross-cut retirement design
> (`ocr-container/docs/specs/2026-05-21-pdomain-ocr-training-retirement-design.md`).

---

## Goals

1. **Core parity** with the current trainer. The working interactive
   feature set of `pdomain-ocr-training/src/pdomain_ocr_training/ui.py` and
   `dataset_ui.py` — profile management, detection/recognition OCR
   config, dataset kanban, detection + recognition training, live
   training log, training runs — must work end-to-end against the same
   on-disk artefacts under `ml-training/<profile>/...`,
   `ml-validation/<profile>/...`, `matched-ocr/`, `dist/`.
2. **Typed REST + SSE surface.** Every UI action has a documented
   FastAPI endpoint; the SPA consumes it via a generated TS client.
   See [`02-backend.md`](02-backend.md).
3. **Single-wheel distribution.** End users install with
   `uv tool install pdomain-ocr-trainer-spa` and get one binary
   (`pdomain-ocr-trainer-ui`) that serves both API and SPA.
   See [`15-deployment-dev.md`](15-deployment-dev.md).
4. **Milestone-implementable by AI agents.** Each milestone in
   [`16-milestones.md`](16-milestones.md) is bounded enough that a
   single coding agent can pick it up, deliver it, and verify against
   the listed acceptance tests.

The legacy trainer's HF-datasets roadmap and the typeface- and
glyph-feature-classifier roadmaps are **not** core-parity scope. They are
carried forward as **deferred post-core-parity milestones** so the design
intent survives the legacy repo's deletion — see *Deferred scope* below.

## Non-goals

- **No replacement for the legacy trainer until core parity ships.**
  Both binaries must coexist on the same machine and on the same
  `ml-training/` tree until `pdomain-ocr-training` is retired. Disk format
  does not change.
- **No new training algorithms.** Detection / recognition training
  entry points live in **`pdomain-ocr-training`** (extracted from the legacy
  `pdomain_ocr_training.train_*` modules); the SPA only drives them through
  the `ITrainingRunner` Protocol. See [`02-backend.md`](02-backend.md).
- **No `torch` in the SPA process.** `torch`/DocTR live only in
  `pdomain-ocr-training`. The FastAPI backend imports the *Protocol* and the
  typed config models, never the concrete training code; training runs
  in a worker subprocess. ([D-T1](17-decisions.md))
- **No NiceGUI / Quasar, no shadcn/ui or direct Tailwind.** The UI is
  React built on the shared **`pdomain-ui`** component library.
  ([D-T19](17-decisions.md))
- **No multi-user collaboration.** One user, possibly multiple browser
  tabs against the same backend, sharing in-memory state.
  ([D-T13](17-decisions.md))
- **No new on-disk dataset format.** Detection parquet, recognition
  imagefolder, `labels.json`, `metadata.jsonl` are byte-for-byte
  preserved per `pdomain-ocr-training/docs/DATASETS.md`.
- **No public REST contract.** The API is intentionally unstable
  across SPA versions. Internal use only — the SPA frontend is the
  only known consumer in v1.
- **No model-training-from-scratch UI work.** Hyperparameter sweeps,
  curriculum design, and architecture choice remain CLI / notebook
  workflows; the SPA exposes the existing knobs (`DetectionConfig` /
  `RecognitionConfig` fields — epochs, batch size, vocab, augmentation
  toggles, …) and nothing more.

## Tech stack

### Backend

| Layer | Choice | Why |
|---|---|---|
| Web framework | **FastAPI** | Same as labeler-spa / pgdp-prep. Pydantic v2, async, OpenAPI export. |
| Server | **uvicorn[standard]** | Same as labeler-spa. |
| Suite plumbing | **`pdomain-ocr-ops` `mount_routes`** | Registry, UI-prefs, sibling-spawn, `/healthz` — not hand-rolled. ([D-T21](17-decisions.md)) |
| Persistence | **Filesystem only** | Single user; profile state, run metadata, datasets all live on disk. |
| Training runner | **`ITrainingRunner` Protocol** from `pdomain-ocr-training`; concrete training runs in a **worker subprocess** running `LocalTrainingRunner` | FastAPI process stays `torch`-free; CUDA isolation + SIGKILL cancellation preserved. ([D-T1](17-decisions.md)) |
| Long jobs | **`pdomain-ocr-ops` `LongJobRunner`** | Job registry, status, SSE progress stream. Training jobs run *minutes to hours* — see [`10-jobs-and-sse.md`](10-jobs-and-sse.md). ([D-T20](17-decisions.md)) |
| Auth | **`IAuth` Protocol**, `none` impl only | Same seam as labeler-spa. |
| Dataset source | **`local` only in core**; `huggingface` is a deferred milestone | HF roadmap deferred — see *Deferred scope*. ([D-T2](17-decisions.md)) |
| Model registry | **`filesystem` (`dist/`) in core**; `huggingface_hub` deferred | Trainer ROADMAP (b)/(d), deferred. |
| Logging | stdlib JSON + `RequestIdMiddleware` | Verbatim port from labeler-spa. |

### Frontend

| Layer | Choice | Why |
|---|---|---|
| Component library | **`pdomain-ui`** (`@pdomain/pdomain-ui`) | `AppShell`, `TopNav`, `Card`, `Accordion`, `Field`/`FieldRow`, `Button`, `Select`, `Progress`, `JobStatusPip`, `useLongJob`, design tokens. ([D-T19](17-decisions.md)) |
| Build | **Vite** | Same as labeler-spa. |
| Framework | **React 19** | Same as labeler-spa. |
| Lang | **TypeScript** strict | Same as labeler-spa. |
| Routing | **`react-router-dom` v7** | Same as labeler-spa. |
| Server state | **`@tanstack/react-query` v5** | Same as labeler-spa. |
| Local state | `useState` + `useReducer`; **`zustand`** for cross-page UI prefs (selected profile, kanban filters, log auto-scroll). | Same pattern as labeler-spa. |
| Styling | **`pdomain-ui` design tokens** (`tokens.css` / `primitives.css`) | No direct Tailwind, no shadcn/ui. ([D-T19](17-decisions.md)) |
| Kanban | pdomain-ui **`KanbanBoard`** (`@dnd-kit`) | Dataset kanban — a pdomain-ui component. ([D-T4](17-decisions.md)) |
| Log viewer | pdomain-ui **`LogViewer`** (`@tanstack/react-virtual`) | Streaming-log viewer — a pdomain-ui component. ([D-T4](17-decisions.md)) |
| Toasts | **`sonner`** | Same as labeler-spa. |
| Hotkeys | **`react-hotkeys-hook`** | Same as labeler-spa. |
| Charts (loss curves, eval) | **`recharts`** | Lightweight, plays well with React 19. ([D-T14](17-decisions.md)) |
| Forms | Controlled inputs + `useMutation` | Same as labeler-spa. |
| Testing (unit) | **Vitest** + **@testing-library/react** | Same as labeler-spa. |
| HTTP mocking | **msw** | Same as labeler-spa. |
| E2E | **Playwright** (Chromium) | Same as labeler-spa. |

**New `pdomain-ui` components.** The trainer needs four components `pdomain-ui`
does not yet have — `KanbanBoard`/`KanbanColumn`/`PageChip`, `LogViewer`,
`Field`/`FieldRow`, and `JobStatusPip`. These are added to `pdomain-ui`
itself rather than built SPA-local, so the suite shares one
implementation. The trainer-spa kanban / log / config milestones depend
on them being specced and built in `pdomain-ui` first; they are tracked as
cross-repo additions to the `pdomain-ui` spec. ([D-T4](17-decisions.md))

### Tooling

| Tool | Notes |
|---|---|
| Python build | `hatchling` + `hatch-vcs`. |
| Wheel-with-SPA | `force-include` the built SPA static dir + a build-hook SPA assertion. |
| Lockfile | `uv.lock`. |
| npm registry | `pdomain-ui` consumed from the self-hosted `pdomain-index-npm` registry. |
| Lint | `ruff` (Python) + `eslint` flat config (TS). |
| Format | `ruff format` + `prettier`. |
| Type-check | TypeScript `strict` + `basedpyright`. |
| Pre-commit | Same hooks as labeler-spa. |
| CI | `lint → test → frontend-build → wheel-build (with SPA assertion) → e2e-browser`; on tag, attach wheel to GitHub Release + publish to `pdomain-index-pip`. |
| Versions | `mise.toml` pinning Node + Python per workspace standard. |

---

## Architectural shape

```
┌──────────────────────────────────────────────────────────────┐
│  Browser (SPA — pdomain-ui components)                            │
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
│  FastAPI (single process — torch-free)                       │
│  ┌──────────────────────┐  ┌────────────────────────────┐    │
│  │  /api/profiles/*     │  │  /api/runs/* (training)    │    │
│  │  /api/datasets/*     │  │  /api/jobs/{id}/events SSE │    │
│  │  /api/models/*       │  │  /api/eval/*               │    │
│  └──────────────────────┘  └────────────────────────────┘    │
│  pdomain-ocr-ops mount_routes: registry · prefs · /healthz        │
│                              │                               │
│  ┌────────── core (in-memory) ────────────────────────┐      │
│  │  AppState ─ Profiles ─ Runs ─ Jobs                 │      │
│  └────────────────────────────────────────────────────┘      │
│                              │                               │
│  ┌─── pdomain-ocr-ops LongJobRunner ───────────────────────┐      │
│  │  job registry · status · SSE event stream          │      │
│  └────────────────────────────┬───────────────────────┘      │
└───────────────────────────────┼───────────────────────────────┘
                                │ spawns
                ┌───────────────▼───────────────┐
                │  training worker subprocess   │
                │  pdomain-ocr-training              │
                │  LocalTrainingRunner →        │
                │  detect / recog (torch+DocTR) │
                └───────────────┬───────────────┘
                                │
                ┌───────────────▼───────────────┐
                │  pdomain-book-tools (Page, Block,  │
                │   Word, BBox)                 │
                └───────────────────────────────┘
```

### Key design rules

1. **`build_app(settings)` factory.** Same as labeler-spa. Every test
   wires its own `Settings` explicitly; the `__main__` script reads
   env vars itself.
2. **In-memory state on `app.state`.** `AppState` lives there; routers
   pull it via `Depends(get_app_state)`. No global singleton.
3. **One state mutation per HTTP request.** Bulk operations land as
   single endpoints with batch payloads.
4. **Persisted changes go through an endpoint; transient UI staging
   does not.** Every change to server state is a mutation endpoint call;
   the server writes through to disk. Transient UI arrangement — notably
   kanban split assignment — is staged client-side and committed by an
   explicit "Apply" batch endpoint ([D-T23](17-decisions.md)). No
   client-side autosave timer.
5. **OpenAPI is source of truth.** `make openapi-export` regenerates
   the TS client types. CI gate: `git diff --exit-code` after re-running.
6. **No backwards-compat shims.** New repo. We read and write the same
   disk layout the legacy trainer uses, with no transient v0 envelopes.
7. **Driver-facing surface is part of the contract.** Every
   `data-testid` and URL shape lives in
   [`13-driver-contract.md`](13-driver-contract.md).
8. **The SPA never imports `torch`.** It drives `pdomain-ocr-training`'s
   `ITrainingRunner` Protocol and the typed `DetectionConfig` /
   `RecognitionConfig` models (which are `torch`-free); the concrete
   `LocalTrainingRunner` runs only inside the worker subprocess.
   ([D-T1](17-decisions.md))

---

## State model

- **Profiles** — profile registry + model-name prefix + base OCR
  profile, stored under the trainer-spa settings path; discovered from
  the `ml-training/` / `ml-validation/` layout.
- **Datasets** — split between `ml-training/<profile>/...` and
  `ml-validation/<profile>/...`. Source pages live in `matched-ocr/`,
  get assigned to splits via the kanban.
- **Runs** — every training run gets a `runs/<run_id>/` directory with
  `args.json`, `stdout`/`stderr`, `progress.jsonl`, status, and
  artefact paths. (The legacy trainer kept runs in-memory only and lost
  logs on tab close — the SPA fixes this.)
- **Jobs** — managed by `pdomain-ocr-ops` `LongJobRunner`: a job registry,
  per-job status, and an SSE event stream. The training subprocess is
  the job's work. The job is **surfaced in the UI** — status pip, live
  progress, streaming log, run history. ([D-T20](17-decisions.md),
  [D-T22](17-decisions.md))
- **Models** — trained artefacts go to `model_output_dir(profile, task)`
  with a sidecar next to the artefact (see [`08-models.md`](08-models.md)).

Backend keeps a single `AppState` (profile registry, dataset index, run
registry) hydrated from disk on startup. Frontend keeps per-tab UI state
in `useState` + `zustand`. Long-running jobs are tracked by the
`LongJobRunner`; reloading the SPA mid-run reattaches to the running
job. ([D-T3](17-decisions.md))

---

## Dataflow per user action

The shape `(user action) → (HTTP/SSE) → (server logic) → (client refetch)`
applies uniformly.

### Reassign pages between splits (kanban) — staged

- Kanban drags rearrange chips in client-side staging state only; no
  request is sent. The UI shows the pending diff against server state.
- On "Apply": `POST /api/profiles/{profile}/datasets/apply` with the
  full target assignment
  (`{train: [...], val: [...], unassigned: [...]}`).
- Server: `ExportManager` (from `pdomain-ocr-training`) reconciles the
  on-disk layout (`ml-training/` / `ml-validation/`) to match; returns
  the new kanban state.
- SPA reconciles cache; staging state clears. "Discard" resets staging
  to server state with no request. ([D-T23](17-decisions.md))

### Start a recognition training run

- SPA calls `POST /api/runs` with `{profile, task: "recognition",
  config: {epochs, batch_size, vocab, ...}}`.
- Server creates `runs/<run_id>/`, writes `args.json`, hands a job to
  the `pdomain-ocr-ops` `LongJobRunner`, returns `202 Accepted` with
  `{run_id, job_id}`.
- The `LongJobRunner` spawns the **training worker subprocess**, which
  builds a `RecognitionConfig` and drives
  `LocalTrainingRunner.train_recognition(...)`. `TrainingEvent`s are
  forwarded as job events (`progress`, `log`, terminal `done`/`error`).
- SPA opens `EventSource(/api/jobs/{job_id}/events)` for live progress.
- On terminal: SPA invalidates the run-detail query; refetch shows final
  status, artefact paths, sidecar.

---

## Deferred scope (post-core-parity milestones)

Carried forward from the legacy trainer so the design intent survives
the repo's deletion; **out of scope for core parity**:

- **HF-datasets roadmap** — `huggingface` `IDatasetSource`, HF model
  publish, per-row licensing. ([D-T2](17-decisions.md),
  [D-T11](17-decisions.md))
- **Typeface-classifier and glyph-feature-classifier training.**

These get their own deferred-milestone specs (retirement plan Task 13).

---

## Milestone contract for AI agents

Every milestone in [`16-milestones.md`](16-milestones.md) follows the
format used in `pdomain-ocr-labeler-spa`:

```
## Mn — short title

**Outcome.** One paragraph: what works at end of milestone.
**Files to create / modify.** Listed.
**Specs that govern this milestone.** Listed.
**Acceptance tests.** pytest / vitest / playwright cases.
**Rollback.** What's not isolated to the listed files.
**Pre-conditions.** What earlier milestones must already exist.
```

If a milestone is too big, split it.

---

## Running spec list (must read before coding)

| If you're touching… | Required reading |
|---|---|
| Anything | `00-overview.md`, `17-decisions.md`, `../docs/context/intent-map.md` |
| Backend route | `01-data-models.md`, `02-backend.md` |
| New page in SPA | `03-frontend.md`, `13-driver-contract.md` |
| Profile / OCR config | `04-profiles-and-config.md` |
| Dataset kanban | `05-dataset-kanban.md`, `12-hotkeys-a11y.md` |
| Training | `06-training-runs.md`, `10-jobs-and-sse.md` |
| Eval | `07-evaluation-and-metrics.md` |
| Model export | `08-models.md` |
| HF integration (deferred) | `09-hf-integration.md` |
| Notifications | `11-notifications.md` |
| Tests | `14-testing.md` |
| Build / install | `15-deployment-dev.md` |
| Roadmap | `16-milestones.md` |

If a question is not answered by the linked spec, **stop and record it in the
[intent map](../docs/context/intent-map.md)** rather than guessing.
