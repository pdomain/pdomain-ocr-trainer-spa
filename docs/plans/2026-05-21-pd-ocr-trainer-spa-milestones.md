---
status: active
synced: ~
milestone: ~
---

# pd-ocr-trainer-spa Milestone Roadmap

This plan tracks the 15 implementation milestones (M0–M14) for `pd-ocr-trainer-spa`, the FastAPI + React/Vite/TypeScript replacement for the legacy NiceGUI `pd-ocr-trainer`. Milestones M0–M3 are infrastructure (no domain UI); M4–M9 are vertical slices (one page + its backend routes); M10–M14 are post-core-parity ROADMAP milestones gated on upstream readiness. Each milestone is bounded to approximately one coding session with concrete acceptance tests. See `specs/16-milestones.md` for the milestone spec and `specs/02`–`specs/19` for the authoritative per-area design (the post-2026-05-21 re-spec onto the pd-ui / pd-ocr-ops / pd-ocr-training stack supersedes any stale impl detail in `16-milestones.md`).

---

## Task 1 — M0 Repo scaffold  {#m0-scaffold}
model: sonnet  effort: M  area: infra

Context: M0 bootstraps the entire `pd-ocr-trainer-spa` repo: pyproject.toml, uv.lock, Makefile, mise.toml, pre-commit, Dockerfile, GitHub Actions workflows (ci/release/nightly), the FastAPI backend skeleton (healthz, env.js, static mount), and a minimal React/Vite/TS frontend serving a static "Hello" SPA. No domain logic is introduced. M0 was already shipped via retirement-plan issue #282 (Scaffold pd-ocr-trainer-spa repo); its GH issue will be created then immediately closed on sync.
Approach: Bootstrap the full repo scaffold modelled on a shipped peer SPA, wiring `pd-ui`, `pd-ocr-ops`, and `pd-ocr-training` as dependencies; add SPA-serving contract tests.
Verification: `make ci` green; `pd-ocr-trainer-ui --no-browser --port 8081 --host 127.0.0.1` serves 200 at `/healthz` and `/`
Acceptance:
- [ ] `make ci` green (backend lint/typecheck/test + frontend install/test)
- [ ] `tests/test_routes_root.py` passes with monkeypatch (no real frontend build required)
- [ ] `pd-ui`, `pd-ocr-ops`, `pd-ocr-training` listed as dependencies
- [ ] GitHub repo created and configured (`allow_squash_merge=false`)

---

## Task 2 — M1 Settings + adapters + AppState seam  {#m1-adapters}
model: sonnet  effort: M  area: backend
Blocked-by: #m0-scaffold

Context: M1 wires every adapter Protocol with its v1 implementation inside `build_app(settings)`, mounts the pd-ocr-ops suite routes, and constructs the pd-ocr-ops `LongJobRunner`. `Fake*` siblings are added for tests. `AppState.hydrate_from_disk` runs on boot but populates nothing yet because no profiles exist. This milestone establishes the adapter layer all subsequent milestones depend on.
Approach: Implement `IStorage`, `IAuth`, `IDatasetSource`, `IModelRegistry` adapter Protocols with real + fake impls plus the `training/` glue package; wire `mount_routes` and a fake `LongJobRunner`; add request-id + error-handler middleware.
Verification: `make ci` green; every adapter Protocol unit-tested with the fake impl
Acceptance:
- [ ] Every adapter Protocol unit-tested with the fake impl
- [ ] `NotImplementedYet` adapters (s3, huggingface) import clean and raise on call
- [ ] Path-traversal guard test on `IStorage.filesystem`

---

## Task 3 — M2 Job runner integration + SSE  {#m2-job-runner}
model: sonnet  effort: M  area: backend
Blocked-by: #m1-adapters

Context: M2 delivers the SPA's `/api/jobs/{id}` + `/api/jobs/{id}/events` SSE endpoints wrapping the pd-ocr-ops `LongJobRunner` (per spec 10). No real run kinds exist yet — tests use a fake `LongJobRunner` scripting synthetic events to drive the full lifecycle including reconnection and cancellation.
Approach: Implement `api/jobs.py` projecting `JobStatus` onto the SPA `Job` model and streaming `stream_events` as SSE; add a TS subscription helper; test reconnect with `Last-Event-ID` and cancel-suppression against the fake runner.
Verification: `make ci` green; SSE integration test passes with synthetic events
Acceptance:
- [ ] Submit a synthetic job; subscribe; receive every scripted event in order
- [ ] Reconnect with `Last-Event-ID:`; missed events replay
- [ ] Cancel; terminal `state` event fires; subsequent events suppressed

---

## Task 4 — M3 Profiles routes + page  {#m3-profiles}
model: sonnet  effort: M  area: fullstack
Blocked-by: #m2-job-runner

Context: M3 ships the working profiles CRUD: list, create, edit, delete with "all" guards. profile.toml round-trips to disk. The React `ProfilesPage` renders the list and dialog on pd-ui primitives. This is the first vertical slice and unlocks all dataset and training milestones gated on profile existence.
Approach: Implement `domain/profiles.py`, `api/profiles.py`, `ProfilesPage`, `ProfileEditDialog`, and a profiles store with full test coverage at each layer.
Verification: `make ci` green; all 6 profile acceptance scenarios pass
Acceptance:
- [ ] Acceptance scenarios 1–6 from `specs/04-profiles-and-config.md` §6
- [ ] Driver-contract testids for profiles inventory present

---

## Task 5 — M4 Datasets kanban (recognition first)  {#m4-kanban-recog}
model: sonnet  effort: M  area: fullstack
Blocked-by: #m3-profiles

Context: M4 delivers the working dataset kanban for `(profile, recognition)` only: client-side staged drag/drop, multi-select, the batch `apply` commit, the "changed" highlight, and rescan. Detection and classifier kanbans share the pd-ui `KanbanBoard` component but their backend endpoint impls land in M5 and M12.
Approach: Implement `domain/datasets.py`, `api/datasets.py`, the `DatasetsPage` composing the pd-ui `KanbanBoard`, and the staged-overlay client state; wire the keyboard-only drag flow.
Verification: `make ci` green; kanban acceptance scenarios pass; keyboard scenario passes
Acceptance:
- [ ] Acceptance scenarios from `specs/05-dataset-kanban.md` §11 (recognition only)
- [ ] Keyboard-only flow: scenario 3 from `specs/12-hotkeys-a11y.md` §9

---

## Task 6 — M5 Detection kanban + training-config defaults  {#m5-kanban-detect}
model: sonnet  effort: M  area: fullstack
Blocked-by: #m4-kanban-recog

Context: M5 adds the detection kanban variant (page chips with bounding-box counts) and the per-profile training-defaults endpoints (GET/PUT/DELETE). `ProfileDetailPage` gains a "Defaults" tab housing the reusable run-args form that M6's run-start form will reuse.
Approach: Extend `domain/datasets.py` for detection; add defaults sub-routes to `api/profiles.py`; implement `ProfileDetailPage` with the Defaults tab and the run-args editor.
Verification: `make ci` green; detection kanban + training-defaults round-trip tests pass
Acceptance:
- [ ] Detection kanban moves pages between unassigned/train/val and `apply` writes valid `labels.json`
- [ ] Training-defaults round-trip for both detection and recognition

---

## Task 7 — M6 Training runs (recognition + detection)  {#m6-runs}
model: sonnet  effort: L  area: fullstack
Blocked-by: #m5-kanban-detect

Context: M6 ships the full training-run lifecycle: start, monitor, cancel a recognition or detection run via the worker subprocess + pd-ocr-ops `LongJobRunner`. SSE log streams into the pd-ui `LogViewer`; `LossChart` populates from progress events. Run-detail and run-list pages work. A sidecar is written next to the model on completion. Crash-recovery (running-at-boot → failed) is verified.
Approach: Implement `domain/runs.py`, `api/runs.py`, the `worker/train.py` subprocess + `training/` glue, frontend run pages, the stub worker fixture, and an e2e lifecycle test.
Verification: `make ci` green; all 6 run acceptance scenarios pass; the slow stub-worker e2e test passes
Acceptance:
- [ ] Acceptance scenarios 1–6 from `specs/06-training-runs.md` §10 (using the fake LongJobRunner)
- [ ] Slow test: real `submit_with_process` + `stub_worker.py` end-to-end
- [ ] Driver-contract testids inventory for run-detail present

---

## Task 8 — M7 Models registry + eval  {#m7-models}
model: sonnet  effort: M  area: fullstack
Blocked-by: #m6-runs

Context: M7 adds model discovery from disk, sidecar viewer, rename, delete, and regenerate-sidecar. An eval form launches an eval run and the result page renders overall metrics. A successful training run from M6 feeds directly into M7's acceptance path.
Approach: Implement `domain/models.py`, `api/models.py`, `api/eval.py`, and the models/eval frontend pages + components.
Verification: `make ci` green; eval round-trip produces `result.json` on disk and renders metrics
Acceptance:
- [ ] Successful train run (M6) yields a sidecar visible in `/models`
- [ ] Eval round-trip: eval submission → `result.json` on disk → page renders metrics
- [ ] Driver-contract testids for models + eval present

---

## Task 9 — M8 Notifications + a11y polish  {#m8-notifications}
model: sonnet  effort: S  area: frontend
Blocked-by: #m7-models

Context: M8 delivers the Sonner toaster and banners as specced in `specs/11-notifications.md`, plus the hotkey help dialog and scope registry from `specs/12-hotkeys-a11y.md`. ARIA roles and `aria-live` regions are added everywhere they were deferred.
Approach: Implement `api/banners.py`, the toaster/banner/hotkey-help components, the `useNotificationStream` and `useHotkey` hooks, and the `errorMessages` map.
Verification: `make ci` green; banner and hotkey scenario tests pass
Acceptance:
- [ ] Banner scenarios from `specs/11-notifications.md` §8
- [ ] Hotkey help dialog tests from `specs/12-hotkeys-a11y.md` §9
- [ ] Coverage smoke test for the error-message map

---

## Task 10 — M9 Driver contract conformance + cutover prep  {#m9-driver-contract}
model: sonnet  effort: S  area: infra
Blocked-by: #m8-notifications

Context: M9 adds a single Playwright conformance spec exercising every URL and testid from `specs/13-driver-contract.md`, and extends `DEVELOPMENT.md` with a "switching from legacy trainer" section. This milestone gates cutover readiness before any production coexistence testing.
Approach: Write `tests/e2e/test_driver_contract.py` covering all driver-contract testids; update `DEVELOPMENT.md` with coexistence instructions and port/env-var separation notes.
Verification: `tests/e2e/test_driver_contract.py` green; manual coexistence check passes
Acceptance:
- [ ] Conformance test green
- [ ] Manual: side-by-side legacy + new `pd-ocr-trainer-ui` against the same `ml-training/` do not collide (different ports, different env-var prefixes)

---

## Task 11 — M10 HF read path  {#m10-hf-read}
model: sonnet  effort: M  area: backend
Blocked-by: #m7-models

Context: M10 implements the Hugging Face dataset read path so recognition runs can pull data from an HF dataset repo. Multi-source mixing across `local + hf` is supported. This is the first post-core-parity ROADMAP milestone (see `specs/18-deferred-hf-datasets.md`) and is gated on M7 (models/eval complete), not M9.
Approach: Implement the real `IDatasetSource.huggingface`; add the `api/sources.py` preview endpoint; extend the run-form UI to add HF dataset sources; add the `HF_TOKEN_PATH` banner.
Verification: `make ci` green; a recognition run with an `hf:` source materializes and trains via the stub worker
Acceptance:
- [ ] A recognition run with `sources=[hf:<repo>@main]` materializes, trains, and writes a sidecar recording the HF source
- [ ] Banner fires when the HF token path is missing

---

## Task 12 — M11 HF publish path (datasets + models)  {#m11-hf-publish}
model: sonnet  effort: M  area: fullstack
Blocked-by: #m10-hf-read

Context: M11 completes the HF integration with the publish path: dataset publish and model publish flows end-to-end against a recorded HF mock. License-gating refuses publish on rows without a `license` field.
Approach: Implement the real `IModelRegistry.huggingface_hub` publish bits; add the `api/publish.py` real flows; implement the publish frontend page + dialog.
Verification: `make ci` green; publish acceptance scenarios from `specs/09-hf-integration.md` §9 pass
Acceptance:
- [ ] Acceptance scenarios from `specs/09-hf-integration.md` §9
- [ ] License-gating refuses publish on rows without `license`

---

## Task 13 — M12 Typeface classifier  {#m12-typeface-classifier}
model: sonnet  effort: L  area: fullstack
Blocked-by: #m11-hf-publish

Context: M12 trains, evaluates, and publishes a typeface classifier (ROADMAP milestone a.5, see `specs/18-deferred-hf-datasets.md`). It adds the typeface kanban variant and per-class eval slicing. Gated on M11 and on the typeface training task existing in `pd-ocr-training` (upstream readiness — OPEN_QUESTIONS Q9).
Approach: Wire the typeface classifier training task from `pd-ocr-training`; add the typeface kanban view + run form; extend the eval metrics table to slice per class.
Verification: `make ci` green; round-trip ingest → train → eval → publish for typeface-classification/v1
Acceptance:
- [ ] Round-trip: ingest a typeface-classification/v1 dataset, train, eval, publish

---

## Task 14 — M13 Glyph eval slicing  {#m13-glyph-eval}
model: sonnet  effort: M  area: fullstack
Blocked-by: #m11-hf-publish

Context: M13 extends recognition eval to support per-glyph-feature slicing and renders the per-feature breakdown (ROADMAP g1, see `specs/19-deferred-glyph-classifier.md`). Gated on M11 and on the `pd-book-tools` `GlyphAnnotations` data model having landed upstream.
Approach: Extend the eval pipeline with slicing logic keyed on `GlyphAnnotations`; add per-feature rows to the eval metrics table.
Verification: `make ci` green; eval slicing acceptance tests from `specs/07-evaluation-and-metrics.md` §8 pass
Acceptance:
- [ ] Acceptance from `specs/07-evaluation-and-metrics.md` §8

---

## Task 15 — M14 Glyph classifier  {#m14-glyph-classifier}
model: opus  effort: L  area: fullstack
Blocked-by: #m13-glyph-eval

Context: M14 trains, evaluates, and publishes the glyph classifier — the large multi-head model (ROADMAP g2, see `specs/19-deferred-glyph-classifier.md`). This is the final post-core-parity milestone, gated on M13 and on `pd-ocr-synth` emitting a `glyph-classification/v1` dataset.
Approach: Wire the glyph classifier training task from `pd-ocr-training`; extend the run form and eval pages for glyph-classifier jobs; publish round-trip against the ROADMAP (g2) ship criterion.
Verification: `make ci` green; round-trip per the ROADMAP (g2) ship criterion
Acceptance:
- [ ] Round-trip per the ROADMAP (g2) ship criterion
