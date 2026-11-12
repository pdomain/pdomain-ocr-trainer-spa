---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-11-12
Kind: context
---

# Intent map

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** deciding what remains active, deferred, blocked, or rejected.
- **Search terms:** intent, roadmap, deferred, blocked, owner decision.

## Active

The backlog text lives in [docs/roadmap.md](../roadmap.md). These are the
active classes:

- **Production typeface training, production eval, and the glyph classifier.**
  See the blocked section and the roadmap. A classifier package waits on
  an owner decision.
- **Publish upload, the unmounted toast hook, the dock row target, the
  `/settings` banner link, and the unused `/env.js` flags.** Open in this
  repository.
- **Run-form device index.** Still an owner decision.
- **Keep lint exceptions auditable.** Any configured or inline suppression must
  remain justified in the
  [lint deviations catalogue](../conventions/lint-deviations.md).

## Open issues

The issue files are evidence for the roadmap rows. They are not a second
backlog.

- [M0–M14 umbrella](../issues/2026-07-21-gh-001-milestone-roadmap.md)
- [M12 Typeface classifier](../issues/2026-07-21-gh-014-m12-typeface-classifier.md)
- [M13 Glyph eval slicing](../issues/2026-07-21-gh-015-m13-glyph-eval-slicing.md)
- [M14 Glyph classifier](../issues/2026-07-21-gh-016-m14-glyph-classifier.md)
- [Jobs surfaces](../issues/2026-07-21-gh-025-unify-jobs-surfaces.md)

## Deferred

Every deferred item, and the reason to wait, is the deferred list on the
[roadmap](../roadmap.md). That includes the progress cap, regression webhook,
HF owner and quota polish, restart durability, per-browser banner dismissal,
`Ctrl+K`, a headless driver repository after a CI pre-pass must drive the
trainer, MPS guidance, labeler deep links, and PageRecord exchange.

## Rejected

- **Regex parser-drift thresholds.** Structured `TrainingEvent` data replaced
  stdout-regex progress parsing, so the former Q14 threshold is obsolete.
- **Couple notice dismissal to freshness.** Per-tab `sessionStorage` dismissal
  remains separate from server-side acknowledgement after a successful kanban
  build.

## Blocked

- **Glyph-classifier training, production typeface training, and production
  eval.** Typeface training calls `train_typeface` on a cast. Production eval
  raises in `_build_runner` and never calls `LocalEvalRunner`. Glyph kanban,
  training defaults, and `create_run` reject that task. Names and issue links
  are on the [roadmap](../roadmap.md).

## Needs owner decision

- **Run-form device index.** The string-to-index mapping, including CPU, is
  undecided. Do not invent it. Details are on the
  [roadmap](../roadmap.md).
- **Toast hook.** Mount `useNotificationStream` or delete it. Do not add a
  third progress surface while that choice is open.
  [Jobs issue](../issues/2026-07-21-gh-025-unify-jobs-surfaces.md).
- **Typeface or glyph classifier package.** `pdomain-ocr-training`
  `docs/ROADMAP.md` keeps that classifier out until the owner confirms the
  scope. If it is built, it is a separate model package. Do not start it now.
  Details are on the [roadmap](../roadmap.md).

Standing open work lives only in [docs/roadmap.md](../roadmap.md).

## Legacy-unverified sweep

- `AGENTS.md`, `CLAUDE.md`, `CODEX.md`, `CONVENTIONS.md`, `DOCGRAPH.md`,
  `README.md`, `DEVELOPMENT.md`, and `docs/process/writing-style.md`: still
  active; rechecked against current commands, configuration, and repository
  structure on 2026-11-07. The documentation check did not run application tests.
- The retired root-level open-question ledger was superseded. Durable unresolved
  items are preserved above, and shipped outcomes are recorded in
  [decisions](decisions.md).
- Shipped behavior is [trainer workflows](../architecture/trainer-workflows.md)
  and [labeler import and freshness](../architecture/labeler-import-and-freshness.md).
  Tombstones for the removed plans are in [decisions](decisions.md).
- `docs/plans/2026-06-10-m12-typeface-classifier.md`: partial on 2026-11-07.
  Keep it until production typeface training is implemented or abandoned.
- `docs/plans/2026-07-14-review-fixes.md`: the suite mount, settings link, and
  chord shortcuts are in the code. Dependency floors have advanced past the
  former pin restriction. Marked partial on 2026-11-07; keep the plan for the
  remaining device-index decision.
- The dep-refresh issue was retired on 2026-11-06. The workflow file is gone.
  See [decisions](decisions.md).
- Root `specs/00` through `specs/12` and `specs/14` through `specs/19`, plus
  `specs/README.md`, were superseded on 2026-11-12. Shipped behavior is in
  `docs/architecture/`. Remaining work is on the roadmap. `specs/13` stays in
  full because `tests/e2e/test_driver_contract.py` parses it. The old "specs
  are the source of truth" line is withdrawn.
