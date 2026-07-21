---
Status: retired
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: decision
---

<!-- markdownlint-disable -->

# Closed GitHub issues archive (cutover 2026-07-21)

## Agent Index

- **Kind:** decision
- **Status:** retired
- **Read when:** recovering verbatim former GitHub issue text after the cutover.
- **Search terms:** GitHub issues archive, former GH, cutover tombstone, issue bodies

## Context

This document archives every GitHub issue that existed on
`pdomain/pdomain-ocr-trainer-spa` at the docs cutover on 2026-07-21 (22 issues:
5 open, 17 closed). Bodies and comments are copied verbatim from `gh issue view`
JSON at cutover time.

## Decision

Keep the full issue text in Git history only. After the add commit lands, remove
this file in a follow-up tombstone commit so the live tree does not carry the
verbatim dump. Open work continues in `docs/roadmap.md` and governed
`docs/issues/` reports.

## Consequences

- Verbatim recovery: `git show <add-sha>:docs/decisions/2026-07-21-github-issues-archive.md`
- Live planning does not depend on this file remaining in the tree.

## Supersedes / Superseded-by

Supersedes the populated GitHub Issues backlog as the permanent body archive.
Does not supersede `docs/roadmap.md` or live governed issue reports.


## #1 — pd-ocr-trainer-spa milestone roadmap (M0–M14)

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/1
- **State:** OPEN
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:03Z
- **Closed:** (open)
- **Labels:** kind:spec, status:backlog

### Body

Tracking spec for the pd-ocr-trainer-spa implementation roadmap.

Plan: docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md

The FastAPI + React/Vite/TS replacement for the legacy pd-ocr-trainer NiceGUI UI. 15 milestones (M0-M14): M0-M3 infrastructure, M4-M9 vertical slices to core parity, M10-M14 post-core-parity ROADMAP milestones. Authoritative design: specs/00-19.

---

## #2 — M0 Repo scaffold

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/2
- **State:** CLOSED (COMPLETED)
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:28Z
- **Closed:** 2026-05-21T15:16:15Z
- **Labels:** kind:feature, status:backlog

### Body

Approach: Bootstrap the full repo scaffold modelled on a shipped peer SPA, wiring `pd-ui`, `pd-ocr-ops`, and `pd-ocr-training` as dependencies; add SPA-serving contract tests.

Plan: [2026-05-21-pd-ocr-trainer-spa-milestones.md#m0-scaffold](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/blob/main/docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md#m0-scaffold)
Verification: `make ci` green; `pd-ocr-trainer-ui --no-browser --port 8081 --host 127.0.0.1` serves 200 at `/healthz` and `/`
Tracks: #1

Acceptance:
- [ ] `make ci` green (backend lint/typecheck/test + frontend install/test)
- [ ] `tests/test_routes_root.py` passes with monkeypatch (no real frontend build required)
- [ ] `pd-ui`, `pd-ocr-ops`, `pd-ocr-training` listed as dependencies
- [ ] GitHub repo created and configured (`allow_squash_merge=false`)

### Comments

#### Comment 1 — ConcaveTrillion @ 2026-05-21T15:16:14Z

M0 shipped via retirement-plan #282 — repo scaffolded, make ci green, GitHub repo created. Closing as already complete.

---

## #3 — M1 Settings + adapters + AppState seam

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/3
- **State:** CLOSED (COMPLETED)
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:29Z
- **Closed:** 2026-05-21T15:59:24Z
- **Labels:** kind:feature, status:backlog

### Body

Approach: Implement `IStorage`, `IAuth`, `IDatasetSource`, `IModelRegistry` adapter Protocols with real + fake impls plus the `training/` glue package; wire `mount_routes` and a fake `LongJobRunner`; add request-id + error-handler middleware.
Blocked by: #2

Plan: [2026-05-21-pd-ocr-trainer-spa-milestones.md#m1-adapters](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/blob/main/docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md#m1-adapters)
Verification: `make ci` green; every adapter Protocol unit-tested with the fake impl
Tracks: #1

Acceptance:
- [ ] Every adapter Protocol unit-tested with the fake impl
- [ ] `NotImplementedYet` adapters (s3, huggingface) import clean and raise on call
- [ ] Path-traversal guard test on `IStorage.filesystem`

### Comments

#### Comment 1 — ConcaveTrillion @ 2026-05-21T15:59:23Z

Shipped on branch feat/m1-adapters. Adapter Protocols (IStorage/IAuth/IDatasetSource/IModelRegistry) + real/fake/NotImplementedYet impls, training/ glue, FakeLongJobRunner, request-id + error-handler middleware, AppState seam wired into build_app. make ci green: ruff + basedpyright clean, 65 backend tests, frontend vitest passing.

---

## #4 — M2 Job runner integration + SSE

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/4
- **State:** CLOSED (COMPLETED)
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:32Z
- **Closed:** 2026-05-21T16:08:59Z
- **Labels:** kind:feature, status:backlog

### Body

Approach: Implement `api/jobs.py` projecting `JobStatus` onto the SPA `Job` model and streaming `stream_events` as SSE; add a TS subscription helper; test reconnect with `Last-Event-ID` and cancel-suppression against the fake runner.
Blocked by: #3

Plan: [2026-05-21-pd-ocr-trainer-spa-milestones.md#m2-job-runner](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/blob/main/docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md#m2-job-runner)
Verification: `make ci` green; SSE integration test passes with synthetic events
Tracks: #1

Acceptance:
- [ ] Submit a synthetic job; subscribe; receive every scripted event in order
- [ ] Reconnect with `Last-Event-ID:`; missed events replay
- [ ] Cancel; terminal `state` event fires; subsequent events suppressed

### Comments

#### Comment 1 — ConcaveTrillion @ 2026-05-21T16:08:59Z

M2 shipped on branch feat/m2-job-runner (worktree pd-ocr-trainer-spa-m2). api/jobs.py implements GET/{id}, GET/{id}/events (SSE), POST/{id}/cancel, GET/active-count; frontend subscribeToJob() helper added. All 3 acceptance criteria covered by tests against the fake runner; make ci green. Not yet pushed.

---

## #5 — M3 Profiles routes + page

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/5
- **State:** CLOSED (COMPLETED)
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:34Z
- **Closed:** 2026-05-21T16:20:09Z
- **Labels:** kind:feature, status:backlog

### Body

Approach: Implement `domain/profiles.py`, `api/profiles.py`, `ProfilesPage`, `ProfileEditDialog`, and a profiles store with full test coverage at each layer.
Blocked by: #4

Plan: [2026-05-21-pd-ocr-trainer-spa-milestones.md#m3-profiles](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/blob/main/docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md#m3-profiles)
Verification: `make ci` green; all 6 profile acceptance scenarios pass
Tracks: #1

Acceptance:
- [ ] Acceptance scenarios 1–6 from `specs/04-profiles-and-config.md` §6
- [ ] Driver-contract testids for profiles inventory present

### Comments

#### Comment 1 — ConcaveTrillion @ 2026-05-21T16:20:08Z

M3 shipped on branch feat/m3-profiles. Domain layer (domain/profiles.py), API routes (api/profiles.py), ProfilesPage, ProfileEditDialog, and profiles store all landed with full test coverage. make ci green (98 backend + 30 frontend tests). Acceptance scenarios 1-6 covered; driver-contract testids present.

---

## #6 — M4 Datasets kanban (recognition first)

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/6
- **State:** CLOSED (COMPLETED)
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:36Z
- **Closed:** 2026-05-21T16:31:09Z
- **Labels:** kind:feature, status:backlog

### Body

Approach: Implement `domain/datasets.py`, `api/datasets.py`, the `DatasetsPage` composing the pd-ui `KanbanBoard`, and the staged-overlay client state; wire the keyboard-only drag flow.
Blocked by: #5

Plan: [2026-05-21-pd-ocr-trainer-spa-milestones.md#m4-kanban-recog](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/blob/main/docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md#m4-kanban-recog)
Verification: `make ci` green; kanban acceptance scenarios pass; keyboard scenario passes
Tracks: #1

Acceptance:
- [ ] Acceptance scenarios from `specs/05-dataset-kanban.md` §11 (recognition only)
- [ ] Keyboard-only flow: scenario 3 from `specs/12-hotkeys-a11y.md` §9

### Comments

#### Comment 1 — ConcaveTrillion @ 2026-05-21T16:31:09Z

M4 shipped on branch feat/m4-datasets-kanban. Backend domain+API for the recognition dataset kanban (build/scan/apply/include-toggles) with staged client-side overlay; DatasetsPage composes the kanban with keyboard-only grab/move/drop. make ci green (118 backend + 46 frontend tests). Note: pd-ui has not published the KanbanBoard component yet, so a vendored shim implementing the pd-ui spec's prop contract is used — to be replaced when pd-ui ships it.

---

## #7 — M5 Detection kanban + training-config defaults

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/7
- **State:** CLOSED (COMPLETED)
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:38Z
- **Closed:** 2026-05-21T16:42:44Z
- **Labels:** kind:feature, status:backlog

### Body

Approach: Extend `domain/datasets.py` for detection; add defaults sub-routes to `api/profiles.py`; implement `ProfileDetailPage` with the Defaults tab and the run-args editor.
Blocked by: #6

Plan: [2026-05-21-pd-ocr-trainer-spa-milestones.md#m5-kanban-detect](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/blob/main/docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md#m5-kanban-detect)
Verification: `make ci` green; detection kanban + training-defaults round-trip tests pass
Tracks: #1

Acceptance:
- [ ] Detection kanban moves pages between unassigned/train/val and `apply` writes valid `labels.json`
- [ ] Training-defaults round-trip for both detection and recognition

### Comments

#### Comment 1 — ConcaveTrillion @ 2026-05-21T16:42:43Z

Shipped on branch feat/m5-detection-kanban. Detection kanban (page chips with bbox counts, apply writes valid labels.json) + training-defaults GET/PUT/DELETE for detection and recognition + ProfileDetailPage Defaults tab with reusable RunArgsEditor. make ci green: 145 backend + 56 frontend tests, lint+typecheck clean.

---

## #8 — M6 Training runs (recognition + detection)

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/8
- **State:** CLOSED (COMPLETED)
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:40Z
- **Closed:** 2026-05-21T17:01:23Z
- **Labels:** kind:feature, status:backlog

### Body

Approach: Implement `domain/runs.py`, `api/runs.py`, the `worker/train.py` subprocess + `training/` glue, frontend run pages, the stub worker fixture, and an e2e lifecycle test.
Blocked by: #7

Plan: [2026-05-21-pd-ocr-trainer-spa-milestones.md#m6-runs](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/blob/main/docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md#m6-runs)
Verification: `make ci` green; all 6 run acceptance scenarios pass; the slow stub-worker e2e test passes
Tracks: #1

Acceptance:
- [ ] Acceptance scenarios 1–6 from `specs/06-training-runs.md` §10 (using the fake LongJobRunner)
- [ ] Slow test: real `submit_with_process` + `stub_worker.py` end-to-end
- [ ] Driver-contract testids inventory for run-detail present

### Comments

#### Comment 1 — ConcaveTrillion @ 2026-05-21T17:01:23Z

M6 shipped on feat/m6-runs. make ci green (lint+typecheck+176 backend+70 frontend tests); slow stub-worker e2e 2/2. All 6 spec-06 §10 acceptance scenarios covered. Driver-contract spec 13 §4.4 extended with run-list + new-run testid inventories.

---

## #9 — M7 Models registry + eval

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/9
- **State:** CLOSED (COMPLETED)
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:42Z
- **Closed:** 2026-05-21T17:16:20Z
- **Labels:** kind:feature, status:backlog

### Body

Approach: Implement `domain/models.py`, `api/models.py`, `api/eval.py`, and the models/eval frontend pages + components.
Blocked by: #8

Plan: [2026-05-21-pd-ocr-trainer-spa-milestones.md#m7-models](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/blob/main/docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md#m7-models)
Verification: `make ci` green; eval round-trip produces `result.json` on disk and renders metrics
Tracks: #1

Acceptance:
- [ ] Successful train run (M6) yields a sidecar visible in `/models`
- [ ] Eval round-trip: eval submission → `result.json` on disk → page renders metrics
- [ ] Driver-contract testids for models + eval present

### Comments

#### Comment 1 — ConcaveTrillion @ 2026-05-21T17:16:20Z

Shipped on branch feat/m7-models. domain/models.py + domain/eval.py + api/models.py + api/eval.py + worker/evaluate.py; models/eval frontend pages + EvalMetricsTable. make ci green (215 backend + 80 frontend tests, lint+typecheck clean). All three acceptance criteria met. Upstream gap surfaced: pd-ocr-training has no eval surface — eval worker uses an injectable runner seam, round-trip proven via stub worker.

---

## #10 — M8 Notifications + a11y polish

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/10
- **State:** CLOSED (COMPLETED)
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:44Z
- **Closed:** 2026-05-21T17:30:10Z
- **Labels:** kind:feature, status:backlog

### Body

Approach: Implement `api/banners.py`, the toaster/banner/hotkey-help components, the `useNotificationStream` and `useHotkey` hooks, and the `errorMessages` map.
Blocked by: #9

Plan: [2026-05-21-pd-ocr-trainer-spa-milestones.md#m8-notifications](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/blob/main/docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md#m8-notifications)
Verification: `make ci` green; banner and hotkey scenario tests pass
Tracks: #1

Acceptance:
- [ ] Banner scenarios from `specs/11-notifications.md` §8
- [ ] Hotkey help dialog tests from `specs/12-hotkeys-a11y.md` §9
- [ ] Coverage smoke test for the error-message map

### Comments

#### Comment 1 — ConcaveTrillion @ 2026-05-21T17:30:09Z

M8 shipped on branch feat/m8-notifications. Backend api/banners.py + domain/banners.py; frontend toaster/banner/hotkey-help components, useNotificationStream + useHotkey hooks, errorMessages map. make ci green (224 backend + 106 frontend tests).

---

## #11 — M9 Driver contract conformance + cutover prep

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/11
- **State:** CLOSED (COMPLETED)
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:46Z
- **Closed:** 2026-05-21T17:40:55Z
- **Labels:** kind:feature, status:backlog

### Body

Approach: Write `tests/e2e/test_driver_contract.py` covering all driver-contract testids; update `DEVELOPMENT.md` with coexistence instructions and port/env-var separation notes.
Blocked by: #10

Plan: [2026-05-21-pd-ocr-trainer-spa-milestones.md#m9-driver-contract](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/blob/main/docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md#m9-driver-contract)
Verification: `tests/e2e/test_driver_contract.py` green; manual coexistence check passes
Tracks: #1

Acceptance:
- [ ] Conformance test green
- [ ] Manual: side-by-side legacy + new `pd-ocr-trainer-ui` against the same `ml-training/` do not collide (different ports, different env-var prefixes)

### Comments

#### Comment 1 — ConcaveTrillion @ 2026-05-21T17:40:54Z

M9 shipped on branch feat/m9-driver-contract. Added tests/e2e/test_driver_contract.py (static, browser-free spec-13 conformance test, runs in make ci), a minimal header chrome (AppHeader: header-bar/version/help-button + sidebar-nav), driverContractVersion in /env.js, and a DEVELOPMENT.md coexistence section. make ci green: 248 backend + 111 frontend tests, ruff + basedpyright clean.

---

## #12 — M10 HF read path

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/12
- **State:** CLOSED (COMPLETED)
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:48Z
- **Closed:** 2026-05-22T10:58:27Z
- **Labels:** kind:feature, status:backlog

### Body

Approach: Implement the real `IDatasetSource.huggingface`; add the `api/sources.py` preview endpoint; extend the run-form UI to add HF dataset sources; add the `HF_TOKEN_PATH` banner.
Blocked by: #9

Plan: [2026-05-21-pd-ocr-trainer-spa-milestones.md#m10-hf-read](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/blob/main/docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md#m10-hf-read)
Verification: `make ci` green; a recognition run with an `hf:` source materializes and trains via the stub worker
Tracks: #1

Acceptance:
- [ ] A recognition run with `sources=[hf:<repo>@main]` materializes, trains, and writes a sidecar recording the HF source
- [ ] Banner fires when the HF token path is missing

---

## #13 — M11 HF publish path (datasets + models)

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/13
- **State:** CLOSED (COMPLETED)
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:50Z
- **Closed:** 2026-05-22T10:48:01Z
- **Labels:** kind:feature, status:backlog

### Body

Approach: Implement the real `IModelRegistry.huggingface_hub` publish bits; add the `api/publish.py` real flows; implement the publish frontend page + dialog.
Blocked by: #12

Plan: [2026-05-21-pd-ocr-trainer-spa-milestones.md#m11-hf-publish](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/blob/main/docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md#m11-hf-publish)
Verification: `make ci` green; publish acceptance scenarios from `specs/09-hf-integration.md` §9 pass
Tracks: #1

Acceptance:
- [ ] Acceptance scenarios from `specs/09-hf-integration.md` §9
- [ ] License-gating refuses publish on rows without `license`

### Comments

#### Comment 1 — ConcaveTrillion @ 2026-05-22T10:48:00Z

Shipped in commit de78100 (CLOSES #13). Backend: POST /api/publish/dataset + /api/publish/model with SPDX license gating and HF token auth. Frontend: PublishPage + PublishDialog + /publish route. make ci green (269+118 tests).

---

## #14 — M12 Typeface classifier

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/14
- **State:** OPEN
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:52Z
- **Closed:** (open)
- **Labels:** kind:feature, status:backlog

### Body

Approach: Wire the typeface classifier training task from `pd-ocr-training`; add the typeface kanban view + run form; extend the eval metrics table to slice per class.
Blocked by: #13

Plan: [2026-05-21-pd-ocr-trainer-spa-milestones.md#m12-typeface-classifier](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/blob/main/docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md#m12-typeface-classifier)
Verification: `make ci` green; round-trip ingest → train → eval → publish for typeface-classification/v1
Tracks: #1

Acceptance:
- [ ] Round-trip: ingest a typeface-classification/v1 dataset, train, eval, publish

### Comments

#### Comment 1 — ConcaveTrillion @ 2026-06-10T22:44:50Z

SPA-side M12 shipped on local main (feat/m12-typeface-classifier, 12 commits ending 77c270a): typeface-classification kanban (metadata.jsonl), run creation, eval round-trip with per-class metrics, TypefaceKanbanPage + driver-contract testids, real Playwright browser verification (9 e2e green). Remaining gate: pdomain-ocr-training must add TypefaceConfig + ITrainingRunner.train_typeface + IEvalRunner.evaluate_typeface (Protocol spec in docs/plans/2026-06-10-m12-typeface-classifier.md §Cross-repo gate — CT to file). Until then the SPA dispatches through the local TypefaceConfig stub + FakeTrainingRunner seam. Leaving open.

---

## #15 — M13 Glyph eval slicing

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/15
- **State:** OPEN
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:54Z
- **Closed:** (open)
- **Labels:** kind:feature, status:backlog

### Body

Approach: Extend the eval pipeline with slicing logic keyed on `GlyphAnnotations`; add per-feature rows to the eval metrics table.
Blocked by: #13

Plan: [2026-05-21-pd-ocr-trainer-spa-milestones.md#m13-glyph-eval](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/blob/main/docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md#m13-glyph-eval)
Verification: `make ci` green; eval slicing acceptance tests from `specs/07-evaluation-and-metrics.md` §8 pass
Tracks: #1

Acceptance:
- [ ] Acceptance from `specs/07-evaluation-and-metrics.md` §8

---

## #16 — M14 Glyph classifier

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/16
- **State:** OPEN
- **Author:** ConcaveTrillion
- **Created:** 2026-05-21T15:15:56Z
- **Closed:** (open)
- **Labels:** kind:feature, status:backlog

### Body

Approach: Wire the glyph classifier training task from `pd-ocr-training`; extend the run form and eval pages for glyph-classifier jobs; publish round-trip against the ROADMAP (g2) ship criterion.
Blocked by: #15

Plan: [2026-05-21-pd-ocr-trainer-spa-milestones.md#m14-glyph-classifier](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/blob/main/docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md#m14-glyph-classifier)
Verification: `make ci` green; round-trip per the ROADMAP (g2) ship criterion
Tracks: #1

Acceptance:
- [ ] Round-trip per the ROADMAP (g2) ship criterion

---

## #17 — [nightly] slow tests failed 2026-05-22

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/17
- **State:** CLOSED (COMPLETED)
- **Author:** app/github-actions
- **Created:** 2026-05-22T06:50:09Z
- **Closed:** 2026-05-22T10:58:27Z
- **Labels:** nightly-failure

### Body

Nightly slow test run failed. See [workflow run](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/actions/runs/26272993307).

---

## #18 — Replace hand-rolled SPDX subset with pd_book_tools.licenses.SPDX_VALID_IDS

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/18
- **State:** CLOSED (COMPLETED)
- **Author:** ConcaveTrillion
- **Created:** 2026-05-22T14:47:51Z
- **Closed:** 2026-05-22T15:06:35Z
- **Labels:** (none)

### Body

Context: pd-book-tools#162 shipped a shared SPDX allowlist (`pd_book_tools.licenses.SPDX_VALID_IDS` / `is_valid_spdx_id`), now merged to pd-book-tools main.

Drop the hand-rolled SPDX subset in `domain/publish.py` and import the canonical allowlist from `pd_book_tools.licenses` instead. Requires bumping the pinned pd-book-tools version once it is released.

### Comments

#### Comment 1 — ConcaveTrillion @ 2026-05-22T15:06:34Z

Shipped in feat/issue-18-spdx-from-pd-book-tools, merged to main. domain/publish.py now imports SPDX_VALID_IDS and is_valid_spdx_id from pd_book_tools.licenses (518 canonical IDs, case-sensitive). 8 new unit tests added.

---

## #19 — Frontend tsc errors on main: publish.ts ApiError arg order, PublishPage profile/Card

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/19
- **State:** CLOSED (COMPLETED)
- **Author:** ConcaveTrillion
- **Created:** 2026-05-22T16:28:47Z
- **Closed:** 2026-05-22T16:36:53Z
- **Labels:** bug, status:backlog

### Body

Three pre-existing `tsc --noEmit` errors on main (frontend has no eslint/typecheck in `make ci` so they slipped in):

- `src/api/publish.ts(42,33)` TS2345 — `new ApiError(message, resp.status, code)` but the canonical `ApiError` constructor signature (profiles.ts) is `(code, message, status)`. Wrong arg order.
- `src/pages/PublishPage.tsx(5,18)` TS6133 — `Card` imported but never used.
- `src/pages/PublishPage.tsx(32,19)` TS2345 — `setProfiles(profilesResp)` but `fetchProfiles()` returns `ProfileListResponse`, not `Profile[]`. Should be `profilesResp.profiles`.

Fix all three and confirm `npx tsc --noEmit` is clean.

---

## #21 — [nightly] slow tests failed 2026-05-23

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/21
- **State:** CLOSED (COMPLETED)
- **Author:** app/github-actions
- **Created:** 2026-05-23T06:13:07Z
- **Closed:** 2026-05-23T19:26:51Z
- **Labels:** nightly-failure

### Body

Nightly slow test run failed. See [workflow run](https://github.com/ConcaveTrillion/pd-ocr-trainer-spa/actions/runs/26325483221).

### Comments

#### Comment 1 — ConcaveTrillion @ 2026-05-23T19:26:50Z

Stale: the sibling-checkout fix (e7d5991) shipped at 12:29 UTC on 2026-05-23, after this run triggered at 06:13 UTC. The current nightly.yml is clean. Next nightly will pass.

---

## #24 — Re-enable downgraded ESLint rules + fix accumulated violations

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/24
- **State:** CLOSED (COMPLETED)
- **Author:** ConcaveTrillion
- **Created:** 2026-05-24T19:24:42Z
- **Closed:** 2026-06-10T22:10:58Z
- **Labels:** (none)

### Body

Background: Workspace Makefile standardization (2026-05-24) added `frontend-lint` via ESLint, but to keep CI green on the existing codebase, several rules were downgraded from `error` to `warn`:

- deprecated `JSX` namespace usage
- `@typescript-eslint/no-invalid-void-type`
- `@typescript-eslint/no-misused-spread`
- accessibility rules (jsx-a11y/*)

**Action:** dedicated cleanup pass to fix all current warnings, then promote the rules back to `error` in `frontend/eslint.config.js`.

Suggested approach:
1. Run `make frontend-lint` to enumerate current warnings.
2. Fix or annotate them in a single PR.
3. Edit `frontend/eslint.config.js` to promote the warn → error.
4. Confirm `make ci` is still green.

Reference: workspace standardization commit $(git -C /workspaces/ocr-container/pd-ocr-trainer-spa rev-parse --short HEAD~1) introduced the relaxed config.

### Comments

#### Comment 1 — ConcaveTrillion @ 2026-06-10T22:10:57Z

All downgraded ESLint rules promoted to error. --max-warnings 0 enforced in the lint script. See worktree chore/eslint-reenable commits for details.

---

## #25 — Unify jobs surfaces: useNotificationStream toasts vs AppShell jobs dock

- **URL:** https://github.com/pdomain/pdomain-ocr-trainer-spa/issues/25
- **State:** OPEN
- **Author:** ConcaveTrillion
- **Created:** 2026-06-10T19:25:41Z
- **Closed:** (open)
- **Labels:** (none)

### Body

Follow-on from the pdomain-ui adoption (Track A, docs/plans/2026-06-10-pdomain-ui-adoption-and-compute-panel.md, Milestone F).

After the AppShell migration, two job-progress surfaces coexist:

- `useNotificationStream` — SSE-driven toasts (pre-existing)
- `useTrainerJobs` — polling hook feeding the AppShell jobs dock (new)

Decision needed: retire the SSE toasts, feed the SSE stream into the dock instead of polling, or keep both deliberately. Scoped out of Track A on purpose.

---
