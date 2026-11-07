---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-11-07
Kind: context
---

# Intent map

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** deciding what remains active, deferred, blocked, or rejected.
- **Search terms:** intent, roadmap, deferred, blocked, owner decision.

## Active

- **Finish production typeface training.** The worker still uses a local
  `TypefaceConfig` and a cast `train_typeface` call. The dataset and API seam
  exist.
  [M12 plan](../plans/2026-06-10-m12-typeface-classifier.md).
  [M12 issue](../issues/2026-07-21-gh-014-m12-typeface-classifier.md).
- **Wire production eval, including glyph slices.** `_build_runner` in
  `worker/evaluate.py` raises. [M13 issue](../issues/2026-07-21-gh-015-m13-glyph-eval-slicing.md).
- **Keep lint exceptions auditable.** Any configured or inline suppression must
  remain justified in the
  [lint deviations catalogue](../conventions/lint-deviations.md).

## Open issues

- [pd-ocr-trainer-spa milestone roadmap (M0–M14)](../issues/2026-07-21-gh-001-milestone-roadmap.md)
  (former GH #1; umbrella)
- [M12 Typeface classifier](../issues/2026-07-21-gh-014-m12-typeface-classifier.md)
  (former GH #14)
- [M13 Glyph eval slicing](../issues/2026-07-21-gh-015-m13-glyph-eval-slicing.md)
  (former GH #15)
- [M14 Glyph classifier](../issues/2026-07-21-gh-016-m14-glyph-classifier.md)
  (former GH #16)
- [Unify jobs surfaces: SSE toasts vs AppShell jobs dock](../issues/2026-07-21-gh-025-unify-jobs-surfaces.md)
  (former GH #25)

## Deferred

- **Progress retention cap.** Revisit the 50,000-event `progress.jsonl` cap only
  if real runs reach it (former Q13).
- **Regression alerts.** Add a repository-local CI webhook script when a
  concrete consumer and endpoint exist (former Q16).
- **Hugging Face defaults and resilience.** Decide whether the token owner's
  identity should populate an empty publish owner, preserve requested source
  weights separately from sampler normalization, and map LFS quota failures to
  actionable UI errors (former Q17, Q18, and Q19).
- **Restart durability.** Persist job event history or supervise detached
  workers only if losing event history or long runs becomes an observed problem
  (former Q20 and Q21).
- **Persistent banner dismissal.** Keep dismissal per tab for now, but revisit
  per-browser persistence if users repeatedly find re-dismissing the same banner
  painful (former Q22). This is a client-side convenience question, separate
  from the rejected idea of coupling dismissal to server freshness state.
- **Command palette.** Add navigation through `Ctrl+K` when navigation friction
  warrants another interaction surface (former Q23).
- **Peer trainer driver.** Add a `pdomain-ocr-trainer-spa-driver` repository only
  if a concrete CI pre-pass needs to create profiles, import known-good exports,
  start training, wait, and archive results (former Q24). The current driver
  contract keeps that option open without creating an unused repository.
- **MPS guidance.** Add architecture-specific or general fallback warnings after
  measurement identifies useful advice (former Q25).
- **Open exports in the labeler.** Add a deep link only after the labeler owns a
  stable project and page URL contract.
- **PageRecord exchange.** Replace the current manifest bridge only when both
  applications can share identity and provenance without application-specific
  behavior. See
  [labeler import and freshness](../architecture/labeler-import-and-freshness.md).

## Rejected

- **Regex parser-drift thresholds.** Structured `TrainingEvent` data replaced
  stdout-regex progress parsing, so the former Q14 threshold is obsolete.
- **Couple notice dismissal to freshness.** Per-tab `sessionStorage` dismissal
  remains separate from server-side acknowledgement after a successful kanban
  build.

## Blocked

- **Glyph-classifier training.** End-to-end support is blocked on typed
  classifier training and configuration contracts in `pdomain-ocr-training`.
- **Production typeface training and evaluation.** The SPA seam exists, but
  upstream runner and real evaluation contracts are not available.

## Needs owner decision

- **Jobs transport residual.** Product direction already keeps both toast and
  dock surfaces. See [decisions.md](decisions.md), 2026-07-14. Only reopen if
  keeping both surfaces should change. Until then, do not add a third progress
  surface. Optional follow-up is an SSE-fed dock or quieter toasts.
  [Jobs issue](../issues/2026-07-21-gh-025-unify-jobs-surfaces.md).
- **Run-form device index.** The string-to-index mapping, including CPU, is
  undecided. Do not invent it. The suite stores a device string.
  `CreateRunRequest.device` is `int | None`. `NewRunPage` does not send it.
  [Review-fixes plan](../plans/2026-07-14-review-fixes.md).

Other deferred items should wait until their stated evidence appears.

Standing open work also lives in [docs/roadmap.md](../roadmap.md).

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
