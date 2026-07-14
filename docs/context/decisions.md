---
Status: active
Owner: CT
Created: 2026-07-14
Last verified: 2026-07-14
Kind: context
---

# Decisions

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** investigating why current architecture differs from older
  plans.
- **Search terms:** decisions, deviations, tombstones, retirement, rationale.

## 2026-07-14: Record shipped architecture instead of milestone projections

The application shipped in a different order from the milestone roadmap. Current
architecture now records the code and test boundaries directly. The partial
typeface plan remains live because browser and API tests prove only the SPA
seam, not production training or evaluation.

## 2026-07-14: Keep notification and job surfaces separate

The notification stream drives transient notices. A separate `GET /api/jobs`
adapter supplies `progress` and `run_id` to the pdomain-ui jobs dock. Both
surfaces remain because they serve different interaction needs.

## 2026-07-14: Use dependency-free SVG charts

The implemented loss visualization uses an SVG component instead of the proposed
Recharts dependency. This keeps chart rendering local and avoids an additional
runtime dependency.

## 2026-07-14: Separate Hugging Face read and publish authority

Reading remote datasets does not authorize writes. Publish routes remain behind
their explicit setting so users cannot upload merely by enabling a read path.

## 2026-07-14: Keep banner dismissal local to a tab

Dismissals use `sessionStorage`. Freshness acknowledgement occurs separately
after a successful kanban build, so hiding a notice cannot mark an export as
consumed.

### 2026-07-14 Retired: Open Questions

- Old path: retired root-level open-question ledger
- Outcome: superseded
- Superseded by: `docs/context/intent-map.md` and current architecture
- Removal commit: (fill after commit)
- Rationale kept: shipped deviations above; worthwhile unbuilt ideas in the
  intent map
- Remaining work: deferred and blocked items in the intent map

### 2026-07-14 Retired: OCR Trainer SPA milestone roadmap

- Old path: `docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md`
- Outcome: implemented and superseded
- Superseded by: `docs/architecture/trainer-workflows.md`
- Removal commit: (fill after commit)
- Rationale kept: architecture deviations and residual typeface/glyph work
- Remaining work: intent-map blocked items and the partial M12 plan

### 2026-07-14 Retired: ESLint rules re-enable plan

- Old path: `docs/plans/2026-06-10-eslint-rules-reenable.md`
- Outcome: implemented
- Superseded by: `docs/architecture/trainer-workflows.md` and
  `docs/conventions/lint-deviations.md`
- Removal commit: (fill after commit)
- Rationale kept: the zero-warning package gate and explicit exception policy
- Remaining work: keep the catalogue synchronized

### 2026-07-14 Retired: Labeler import discovery plan

- Old path: `docs/plans/2026-06-10-labeler-import-discovery.md`
- Outcome: implemented with deviations
- Superseded by: `docs/architecture/labeler-import-and-freshness.md`
- Removal commit: (fill after commit)
- Rationale kept: dynamic mode reporting and separate acknowledgement/dismissal
  boundaries
- Remaining work: deferred deep link and PageRecord exchange

### 2026-07-14 Retired: pdomain-ui adoption and compute panel plan

- Old path: `docs/plans/2026-06-10-pdomain-ui-adoption-and-compute-panel.md`
- Outcome: implemented with deviations
- Superseded by: `docs/architecture/trainer-workflows.md`
- Removal commit: (fill after commit)
- Rationale kept: shared shell, compute panel, jobs dock, and notification
  coexistence
- Remaining work: none specific to the retired plan

### 2026-07-14 Retired: Process lint deviations

- Old path: `docs/process/lint-deviations.md`
- Outcome: superseded duplicate
- Superseded by: `docs/conventions/lint-deviations.md`
- Removal commit: (fill after commit)
- Rationale kept: builder and jobs Protocol suppressions in the unified
  catalogue
- Remaining work: none
