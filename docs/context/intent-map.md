---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-21
Kind: context
---

# Intent map

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** deciding what remains active, deferred, blocked, or rejected.
- **Search terms:** intent, roadmap, deferred, blocked, owner decision.

## Active

- **Complete the typeface production round-trip.** Keep the existing dataset,
  SPA, and API seam aligned while upstream `TypefaceConfig`, `train_typeface`,
  and real evaluation remain unfinished. Evidence:
  [partial M12 plan](../plans/2026-06-10-m12-typeface-classifier.md). Standing
  backlog: [roadmap](../roadmap.md) (former GH #14 / M12).
- **Unify jobs surfaces.** Resolve dual progress UI (SSE toasts vs AppShell
  jobs dock). Governed issue:
  [unify jobs surfaces](../issues/2026-07-21-gh-025-unify-jobs-surfaces.md)
  (former GH #25).
- **Keep lint exceptions auditable.** Any configured or inline suppression must
  remain justified in the
  [lint deviations catalogue](../conventions/lint-deviations.md).

## Open issues

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

- **Jobs transport residual** (former GH #25): product direction already keeps
  both toast and dock surfaces
  ([decisions.md](decisions.md) 2026-07-14). Only reopen if that dual UX should
  change. Until then, do not add a third progress surface; optional follow-up is
  SSE-fed dock or quieter toasts.

Other deferred items should remain parked until their stated evidence appears.

Standing open work also lives in [docs/roadmap.md](../roadmap.md).

## Legacy-unverified sweep

- `AGENTS.md`, `CLAUDE.md`, `CONVENTIONS.md`, `DEVELOPMENT.md`, and
  `docs/process/writing-style.md`: still active; verified against current
  commands and conventions on 2026-07-14.
- The retired root-level open-question ledger was superseded. Durable unresolved
  items are preserved above, and shipped outcomes are recorded in
  [decisions](decisions.md).
- The implemented milestone, ESLint, labeler-import, and pdomain-ui plans were
  retired and removed in this staged migration. Their shipped behavior now
  lives in [trainer workflows](../architecture/trainer-workflows.md) and
  [labeler import and freshness](../architecture/labeler-import-and-freshness.md);
  durable rationale and readable tombstones live in
  [decisions](decisions.md), with remaining work preserved in this intent map.
- `docs/plans/2026-06-10-m12-typeface-classifier.md`: partial; keep until the
  upstream production round-trip is implemented or deliberately abandoned.
