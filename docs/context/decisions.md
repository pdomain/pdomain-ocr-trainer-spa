---
Status: active
Owner: CT
Created: 2026-07-14
Last verified: 2026-11-12
Kind: context
---

# Decisions

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** investigating why current architecture differs from older
  plans.
- **Search terms:** decisions, deviations, tombstones, retirement, rationale.

## 2026-11-06: GitHub workflows removed; release is local

Commit `f5437b31f3d44fddbfc8cf66f44fc3d0e7c6a6b8` deleted every GitHub Actions
workflow, including dep-refresh, nightly, CI, and the old release workflow.
Branch protection is off. `scripts/do-release.sh` tags `master` and creates the
GitHub Release on this machine. The dated dep-refresh branch cannot accumulate
here, because that workflow file is gone.

## 2026-07-21: Cut over GitHub Issues into governed docs

Planning moved out of the remote issue tracker. Standing backlog is
`docs/roadmap.md`. Evidence-bearing defects use `docs/issues/`. Full issue
bodies at cutover live in a Git history tombstone (archive add commit, then
removed from the live tree). Full write-up:
[GitHub Issues cutover](../decisions/2026-07-21-github-issues-cutover.md).

## 2026-07-14: Record shipped architecture instead of milestone projections

The application shipped in a different order from the milestone roadmap. Current
architecture now records the code and test boundaries directly. The partial
typeface plan remains live because browser and API tests prove only the SPA
seam, not production training or evaluation.

## 2026-07-14: Keep notification and job surfaces separate

The notification stream drives transient notices. A separate `GET /api/jobs`
adapter supplies `progress` and `run_id` to the pdomain-ui jobs dock. Both
surfaces remain because they serve different interaction needs.

Corrected 2026-11-12: `useNotificationStream` is not mounted, so those toasts
do not fire. The dock poll and the run-detail SSE stream are the live
surfaces. See the 2026-11-12 entry below.

## 2026-07-14: Use dependency-free SVG charts

The implemented loss visualization uses an SVG component instead of the proposed
Recharts dependency. This keeps chart rendering local and avoids an additional
runtime dependency.

## 2026-07-14: Separate Hugging Face read and publish authority

Reading remote datasets does not authorize writes. Publish routes remain behind
their explicit setting so users cannot upload merely by enabling a read path.

Corrected 2026-11-12: preview is implemented. Publish helpers raise
`AdapterNotImplementedError`. `enable_hf_publish` is not checked by the
routes or the React app. See the 2026-11-12 entry below.

## 2026-07-14: Keep banner dismissal local to a tab

Dismissals use `sessionStorage`. Freshness acknowledgement occurs separately
after a successful kanban build, so hiding a notice cannot mark an export as
consumed.

### 2026-07-14 Retired: Open Questions

- Old path: retired root-level open-question ledger
- Outcome: superseded
- Superseded by: `docs/context/intent-map.md` and current architecture
- Removal commit: `13758cc375fb06d83359a1e3407c41c6474eb2f9`
- Rationale kept: shipped deviations above; worthwhile unbuilt ideas in the
  intent map
- Remaining work: deferred and blocked items in the intent map

### 2026-07-14 Retired: OCR Trainer SPA milestone roadmap

- Old path: `docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md`
- Outcome: implemented and superseded
- Superseded by: `docs/architecture/trainer-workflows.md`
- Removal commit: `13758cc375fb06d83359a1e3407c41c6474eb2f9`
- Rationale kept: architecture deviations and residual typeface/glyph work
- Remaining work: intent-map blocked items and the partial M12 plan

### 2026-07-14 Retired: ESLint rules re-enable plan

- Old path: `docs/plans/2026-06-10-eslint-rules-reenable.md`
- Outcome: implemented
- Superseded by: `docs/architecture/trainer-workflows.md` and
  `docs/conventions/lint-deviations.md`
- Removal commit: `13758cc375fb06d83359a1e3407c41c6474eb2f9`
- Rationale kept: the zero-warning package gate and explicit exception policy
- Remaining work: keep the catalogue synchronized

### 2026-07-14 Retired: Labeler import discovery plan

- Old path: `docs/plans/2026-06-10-labeler-import-discovery.md`
- Outcome: implemented with deviations
- Superseded by: `docs/architecture/labeler-import-and-freshness.md`
- Removal commit: `13758cc375fb06d83359a1e3407c41c6474eb2f9`
- Rationale kept: dynamic mode reporting and separate acknowledgement/dismissal
  boundaries
- Remaining work: deferred deep link and PageRecord exchange

### 2026-07-14 Retired: pdomain-ui adoption and compute panel plan

- Old path: `docs/plans/2026-06-10-pdomain-ui-adoption-and-compute-panel.md`
- Outcome: implemented with deviations
- Superseded by: `docs/architecture/trainer-workflows.md`
- Removal commit: `13758cc375fb06d83359a1e3407c41c6474eb2f9`
- Rationale kept: shared shell, compute panel, jobs dock, and notification
  coexistence
- Remaining work: none specific to the retired plan

### 2026-07-14 Retired: Process lint deviations

- Old path: `docs/process/lint-deviations.md`
- Outcome: superseded duplicate
- Superseded by: `docs/conventions/lint-deviations.md`
- Removal commit: `13758cc375fb06d83359a1e3407c41c6474eb2f9`
- Rationale kept: builder and jobs Protocol suppressions in the unified
  catalogue
- Remaining work: none

### 2026-11-06 Retired: dep-refresh cannot auto-land

- Old path: `docs/issues/2026-08-08-dep-refresh-cannot-auto-land.md`
- Outcome: superseded
- Superseded by: [DEVELOPMENT.md](../../DEVELOPMENT.md) section "Cut a release
  locally" and `scripts/do-release.sh`
- Removal commit: `d9fb2ffbccbba063d11f96181b69815b2fd367a1`
- Rationale kept: the 2026-11-06 decision above. Owner commit
  `f5437b31f3d44fddbfc8cf66f44fc3d0e7c6a6b8` removed `.github/workflows`.
- Remaining work: none

### 2026-11-09 Retired: issue-tracker migration handoff and the empty archive folder

- Old paths: `docs/handoff/2026-07-17-issue-tracker-migration.md` and `docs/archive/.gitkeep`
- Outcome: deleted; retired docs live in Git history, not the live tree or an archive folder
- Superseded by: [GitHub issues cutover](../decisions/2026-07-21-github-issues-cutover.md)
- Removal commit: `79aca57d`
- Rationale kept: The handoff was already retired on 2026-07-21 when the cutover ran. Read it with
  `git show c94d3de:docs/handoff/2026-07-17-issue-tracker-migration.md`.
- Remaining work: none

## 2026-11-12: Root design specs are not current truth

The numbered files in `specs/` still said they were the source of truth after
architecture notes had become the shipped record. A review against the code
on this date found the drift recorded in the architecture pages and the
roadmap: charts are SVG, there is no generated client and no GitHub
workflows, publish does not upload, and the toast hook is not mounted.

Shipped behavior now lives under `docs/architecture/`. Remaining work lives
only in `docs/roadmap.md`. Unbuilt routes from those specs (settings page,
vocab scan, runtime device list, S3, source list, ndjson log) are dropped,
not queued.

`specs/13-driver-contract.md` stays in full. `tests/e2e/test_driver_contract.py`
parses its tables. The other numbered specs are superseded stubs. Their old
bodies are in git history.

### 2026-11-12 Retired: root design specs

- Old path: `specs/00-overview.md` through `specs/12-hotkeys-a11y.md`, and
  `specs/14-testing.md` through `specs/19-deferred-glyph-classifier.md`, plus
  `specs/README.md`
- Outcome: superseded
- Superseded by: `docs/architecture/` and `docs/roadmap.md`
- Removal commit: (fill after commit)
- Rationale kept: architecture pages for shipped behavior; roadmap for open,
  deferred, and dropped work
- Remaining work: the roadmap. `specs/13-driver-contract.md` is not part of
  this retirement.
