# 16 — Milestones

The roadmap. Each milestone is bounded enough that a single AI
coding agent can deliver it in one session, with the listed
acceptance tests passing.

> **Required reading before starting any milestone:**
> [`00-overview.md`](00-overview.md), [`OPEN_QUESTIONS.md`](../OPEN_QUESTIONS.md),
> the per-area specs listed in the milestone.

Milestones M0–M3 are infrastructure (no domain UI). M4–M9 each
ship a vertical slice (one page + the routes behind it). M10+ are
ROADMAP-driven (HF, classifier tasks, glyph).

---

## M0 — Repo scaffold

**Outcome.** A repo that lints, type-checks, builds an empty wheel,
boots `pd-ocr-trainer-ui` and serves a static "Hello" SPA. No
domain logic.

**Files to create.**

```
pd-ocr-trainer-spa/
├── pyproject.toml
├── uv.lock
├── Makefile
├── mise.toml
├── .pre-commit-config.yaml
├── .gitignore
├── DEVELOPMENT.md
├── Dockerfile
├── install.sh / install.ps1
├── build_hooks/spa_check.py
├── .github/workflows/{ci,release,nightly}.yml
├── src/pd_ocr_trainer_spa/
│   ├── __init__.py
│   ├── __main__.py
│   ├── bootstrap.py
│   ├── settings.py
│   ├── api/healthz.py
│   ├── api/env_js.py
│   └── static/.gitkeep
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   ├── vitest.config.ts
│   ├── tsconfig.{json,app.json,node.json}
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── eslint.config.ts
│   ├── components.json
│   ├── index.html
│   └── src/{main.tsx, App.tsx, index.css, routes.ts, api/{client,types}.ts, test/setup.ts}
└── tests/
    ├── conftest.py
    └── unit/{test_healthz.py, test_settings.py}
```

**Specs that govern.**
- [`00-overview.md`](00-overview.md), [`02-backend.md`](02-backend.md) §1–§3,
  [`03-frontend.md`](03-frontend.md) §1–§2, [`15-deployment-dev.md`](15-deployment-dev.md).

**Acceptance tests.**
- `make setup && make test` green.
- `make frontend-test` green (one smoke test).
- `make frontend-build` produces `dist/` and copies into static/.
- `make build` produces a wheel; `python -m zipfile -l <whl>` shows
  `pd_ocr_trainer_spa/static/index.html`.
- `pd-ocr-trainer-ui --no-browser --port 8081 --host 127.0.0.1`
  responds 200 to `/healthz` and serves index.html at `/`.
- `make openapi-export` produces `frontend/openapi.json` and
  `frontend/src/api/types.ts`.
- ESLint and ruff pass clean. Pre-commit installed and passing.

**Pre-conditions.** None.

---

## M1 — Settings + adapters + AppState seam

**Outcome.** `build_app(settings)` wires every adapter Protocol with
its v1 impl. `Fake*` siblings exist for tests. `AppState.hydrate_from_disk`
runs on boot but populates nothing yet (no profiles to discover).

**Files.**
- `src/pd_ocr_trainer_spa/core/{app_state,paths,errors}.py`
- `src/pd_ocr_trainer_spa/adapters/storage/{__init__,filesystem,s3}.py`
- `src/pd_ocr_trainer_spa/adapters/auth/{__init__,none}.py`
- `src/pd_ocr_trainer_spa/adapters/training/{__init__,local_subprocess,modal,shared_container,fake}.py`
- `src/pd_ocr_trainer_spa/adapters/dataset_sources/{__init__,local,huggingface,fake}.py`
- `src/pd_ocr_trainer_spa/adapters/model_registry/{__init__,filesystem,huggingface_hub,fake}.py`
- `src/pd_ocr_trainer_spa/middleware/{request_id,error_handler}.py`
- `tests/unit/adapters/...`

**Specs.** [`02-backend.md`](02-backend.md) §4, [`14-testing.md`](14-testing.md) §2.1.

**Acceptance.**
- Every adapter Protocol unit-tested with the fake impl.
- `local_subprocess` and `huggingface_*` impls raise `NotImplementedYet`
  when called without a target — but their *modules import* clean.
- Path-traversal guard test on `IStorage.filesystem`.

---

## M2 — Job runner + SSE

**Outcome.** `JobRunner` exists and works; `/api/jobs/{id}/events`
serves SSE end-to-end with replay. No real run kinds yet — tests
use synthetic events.

**Files.**
- `src/pd_ocr_trainer_spa/core/{job_runner,notifications}.py`
- `src/pd_ocr_trainer_spa/api/jobs.py`
- `frontend/src/api/jobs.ts` (subscribeToJob)
- `tests/integration/api/test_jobs_sse.py`
- `tests/unit/core/test_job_runner.py`

**Specs.** [`10-jobs-and-sse.md`](10-jobs-and-sse.md), [`02-backend.md`](02-backend.md) §5.5.

**Acceptance.**
- Submit a synthetic job; subscribe; receive every scripted event in order.
- Reconnect with `Last-Event-ID:`; missed events replay.
- Cancel; `cancelled` event fires; subsequent events suppressed.

---

## M3 — Profiles routes + page

**Outcome.** Working profiles list, create, edit, delete (with the
"all" guards). Disk side-effects verified. Profile.toml round-trips.
ProfilesPage in the SPA renders the list + dialog.

**Files.**
- `src/pd_ocr_trainer_spa/domain/profiles.py`
- `src/pd_ocr_trainer_spa/api/profiles.py`
- `frontend/src/pages/ProfilesPage.tsx`
- `frontend/src/components/ProfileEditDialog.tsx`
- `frontend/src/hooks/useProfiles.ts`
- tests across all the above.

**Specs.** [`04-profiles-and-config.md`](04-profiles-and-config.md), [`01-data-models.md`](01-data-models.md) §1.

**Acceptance.**
- Acceptance scenarios 1–6 from
  [`04-profiles-and-config.md`](04-profiles-and-config.md) §6.
- Driver-contract testids for profiles inventory present.

---

## M4 — Datasets kanban (recognition first)

**Outcome.** Working kanban for `(profile, recognition)` only.
Drag/drop, multi-select, copy-to-datasets, "yellow changed"
highlight, refresh. Detection / classifier kanbans ride along the
same component but their endpoint impls land in M5+.

**Files.**
- `src/pd_ocr_trainer_spa/domain/datasets.py`
- `src/pd_ocr_trainer_spa/api/datasets.py`
- `frontend/src/pages/DatasetsPage.tsx`
- `frontend/src/components/{KanbanBoard,KanbanColumn,KanbanCard,PageChip}.tsx`
- `frontend/src/stores/selection.ts`
- tests across all the above.

**Specs.** [`05-dataset-kanban.md`](05-dataset-kanban.md), [`01-data-models.md`](01-data-models.md) §2,
[`12-hotkeys-a11y.md`](12-hotkeys-a11y.md) §3.1.

**Acceptance.**
- Acceptance scenarios 1–6 from
  [`05-dataset-kanban.md`](05-dataset-kanban.md) §11 (recognition only).
- Keyboard-only flow: scenario 3 from
  [`12-hotkeys-a11y.md`](12-hotkeys-a11y.md) §9.

**Pre-conditions.** M3.

---

## M5 — Detection kanban + training-config defaults

**Outcome.** Detection kanban variant works (page chips with bbox
counts). Per-profile training-defaults endpoints (GET/PUT/DELETE)
ship; ProfileDetailPage gains a "Defaults" tab.

**Files.**
- `domain/datasets.py` extension for detection.
- `api/profiles.py` defaults sub-routes.
- `frontend/src/pages/{ProfileDetailPage}.tsx` (defaults tab).
- `frontend/src/components/RunArgsEditor.tsx` (the form, for reuse in M6).

**Specs.** [`04-profiles-and-config.md`](04-profiles-and-config.md) §3, [`05-dataset-kanban.md`](05-dataset-kanban.md) §10.

**Acceptance.**
- Detection kanban can move pages between unassigned/train/val and
  copy-to-datasets writes valid `labels.json`.
- Training-defaults round-trip for both detection and recognition.

**Pre-conditions.** M4.

---

## M6 — Training runs (recognition + detection)

**Outcome.** Start, monitor, cancel a recognition or detection run.
SSE log streams; LossChart populates from progress events.
Run-detail and run-list pages work. Sidecar written next to model.
Crash-recovery (running-at-boot → failed) verified.

**Files.**
- `src/pd_ocr_trainer_spa/domain/runs.py` (Run model + on-disk persistence + hydrate)
- `src/pd_ocr_trainer_spa/api/runs.py`
- `src/pd_ocr_trainer_spa/adapters/training/parsers.py`
- `frontend/src/pages/{RunsPage,RunDetailPage}.tsx`
- `frontend/src/components/{RunForm,RunStatusBadge,RunProgressBar,LogViewer,LossChart}.tsx`
- `tests/fixtures/training_logs/*.txt`
- `tests/fixtures/stub_trainer.py`
- `tests/e2e/test_run_lifecycle.py`

**Specs.** [`06-training-runs.md`](06-training-runs.md), [`10-jobs-and-sse.md`](10-jobs-and-sse.md), [`14-testing.md`](14-testing.md) §5.

**Acceptance.**
- Acceptance scenarios 1–6 from
  [`06-training-runs.md`](06-training-runs.md) §10 (using FakeTrainingRunner).
- Slow test: real `local_subprocess` + `stub_trainer.py` end-to-end.
- Driver-contract testids inventory for run-detail present.

**Pre-conditions.** M5.

---

## M7 — Models registry + eval

**Outcome.** Models discovered from disk, displayed, sidecar
viewer, rename, delete, regenerate-sidecar. Eval form launches an
eval run; result page renders overall metrics.

**Files.**
- `src/pd_ocr_trainer_spa/domain/models.py`
- `src/pd_ocr_trainer_spa/api/models.py`
- `src/pd_ocr_trainer_spa/api/eval.py`
- `frontend/src/pages/{ModelsPage,ModelDetailPage,EvalPage,EvalResultPage}.tsx`
- `frontend/src/components/{ModelCard,ModelSidecarView,EvalMetricsTable}.tsx`

**Specs.** [`07-evaluation-and-metrics.md`](07-evaluation-and-metrics.md), [`08-models.md`](08-models.md).

**Acceptance.**
- Successful train run (M6) yields a sidecar visible in /models.
- Eval round-trip: eval submission → result.json on disk → page renders metrics.
- Driver-contract testids for models + eval present.

**Pre-conditions.** M6.

---

## M8 — Notifications + a11y polish

**Outcome.** Sonner toaster + banners work as specced. Hotkey
help dialog and scope registry land. ARIA role/aria-live everywhere.

**Files.**
- `src/pd_ocr_trainer_spa/api/banners.py`
- `frontend/src/components/{NotificationToaster,HotkeyHelpDialog,Banners}.tsx`
- `frontend/src/hooks/{useNotificationStream,useHotkey}.ts`
- `frontend/src/lib/errorMessages.ts`

**Specs.** [`11-notifications.md`](11-notifications.md), [`12-hotkeys-a11y.md`](12-hotkeys-a11y.md).

**Acceptance.**
- Banner scenarios from [`11-notifications.md`](11-notifications.md) §8.
- Hotkey help dialog tests from [`12-hotkeys-a11y.md`](12-hotkeys-a11y.md) §9.
- Code-coverage smoke test for error-message map.

**Pre-conditions.** M7.

---

## M9 — Driver contract conformance + cutover prep

**Outcome.** Single Playwright spec exercises every URL + testid in
[`13-driver-contract.md`](13-driver-contract.md). DEVELOPMENT.md gets
a "switching from legacy trainer" section.

**Files.**
- `tests/e2e/test_driver_contract.py`
- `DEVELOPMENT.md` updates.

**Specs.** [`13-driver-contract.md`](13-driver-contract.md).

**Acceptance.**
- Conformance test green.
- Manual: a side-by-side run of legacy `pd-ocr-trainer-ui` and new
  `pd-ocr-trainer-ui` against the same `ml-training/` does not
  step on each other (different ports, different env-var prefixes).

**Pre-conditions.** M8.

---

## M10 — HF read path

**Outcome.** Recognition runs can pull data from a Hugging Face
dataset. Trainer ROADMAP milestone (a) for the SPA. Multi-source
mixing across `local + hf` works.

**Files.**
- Real impls of `IDatasetSource.huggingface`.
- `api/sources.py` preview endpoint.
- Run-form UI for adding HF sources.

**Specs.** [`09-hf-integration.md`](09-hf-integration.md) §3–§4.

**Acceptance.**
- A recognition run with `sources=[hf:<repo>@main]` materializes,
  trains (via stub_trainer), and writes a sidecar with the HF
  source recorded.
- Banner fires when `HF_TOKEN_PATH` is missing.

**Pre-conditions.** M7.

---

## M11 — HF publish path (datasets + models)

**Outcome.** Publish endpoints work end-to-end against a recorded
HF mock. Dataset publish + model publish flows in the UI.

**Files.**
- Real impls of `IModelRegistry.huggingface_hub` (publish bits).
- `api/publish.py` real flows.
- `frontend/src/pages/PublishPage.tsx`
- `frontend/src/components/PublishDialog.tsx`

**Specs.** [`09-hf-integration.md`](09-hf-integration.md) §5–§6.

**Acceptance.**
- Acceptance scenarios from [`09-hf-integration.md`](09-hf-integration.md) §9.
- License-gating refuses publish on rows without `license`.

**Pre-conditions.** M10.

---

## M12 — Typeface classifier (ROADMAP a.5)

**Outcome.** Train + eval + publish a typeface classifier. Adds the
typeface kanban variant.

**Files.**
- New `train_typeface.py` in pd-ocr-trainer (or pd-ocr-trainer-core).
- SPA: typeface kanban view, run form, eval slicing per class.

**Specs.** [`06-training-runs.md`](06-training-runs.md) §5.3, [`07-evaluation-and-metrics.md`](07-evaluation-and-metrics.md) §5.

**Acceptance.**
- Round-trip: ingest typeface-classification/v1 dataset, train,
  eval, publish.

**Pre-conditions.** M11. Trainer-side `train_typeface.py` must exist
([Q3](../OPEN_QUESTIONS.md)).

---

## M13 — Glyph eval slicing (ROADMAP g1)

**Outcome.** Recognition eval supports `slice_glyph_features=true`
and renders the per-feature breakdown.

**Files.**
- Eval pipeline gains slicing logic.
- Frontend `EvalMetricsTable` renders slices.

**Specs.** [`07-evaluation-and-metrics.md`](07-evaluation-and-metrics.md) §4.

**Acceptance.**
- Acceptance from [`07-evaluation-and-metrics.md`](07-evaluation-and-metrics.md) §8.

**Pre-conditions.** M11. `pd-book-tools` `GlyphAnnotations` data model
landed.

---

## M14 — Glyph classifier (ROADMAP g2)

**Outcome.** Train + eval + publish a glyph classifier. The big
multi-head model.

**Specs.** [`06-training-runs.md`](06-training-runs.md) §5.4.

**Acceptance.** Round-trip per ROADMAP (g2) ship criterion.

**Pre-conditions.** M13, plus pd-ocr-synth emitting glyph-classification/v1.

---

## Notes on milestone shape

- Each milestone targets ~one PR, ~one coding session.
- Slow tests are explicitly opt-in (nightly only) so milestones
  don't block on long CI.
- Backwards compatibility with the legacy trainer is a function of
  *coexistence*, not interop: both write the same disk format
  in-place, neither tries to read the other's running state.
- M10 onward is gated by upstream readiness (the legacy
  `train_typeface.py`, `pd-book-tools.GlyphAnnotations`, etc.). The
  SPA waits.
