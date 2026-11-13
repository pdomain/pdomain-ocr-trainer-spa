---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-13
Kind: process
Level: I1
---

# Issues

## Agent Index

- **Kind:** process
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-11-13
- **Read when:** filing a bug / defect / investigation report, or looking up an
  open issue's status, evidence, or resolution.
- **Search terms:** issues folder, bug report, defect report, issue template,
  issue lifecycle, kind issue.

## Purpose

`docs/issues/` holds **governed, evidence-bearing issue reports** — bugs, silent
failures, regressions, and investigations that need a durable, citable record
(not a throwaway chat summary). Each report is a docgraph node so it is
retrievable, linkable from specs/plans/context, and carried in the repo rather
than in per-machine harness memory.

## Convention

- **Location:** `docs/issues/`
- **Filename:** `YYYY-MM-DD-short-slug.md` (creation date + a terse kebab slug).
- **Metadata:** YAML frontmatter **and** a matching `## Agent Index` block. Keep
  frontmatter `Status:` and Agent Index `Status:` identical — a mismatch trips a
  `field_conflict` (→ `status-reconciler`).
  - `Kind: issue`
  - `Level:` informational scope — `I1` repo-wide, `I2` narrow/local.
  - `Status:` governed lifecycle, **not** the issue's open/closed state (see below).
- **Issue state vs governed status:** the docgraph lifecycle is
  `draft → active → implemented → retired`. Express the *issue's* resolution state
  as a separate **`Resolution:`** line in the Agent Index (`Open` / `Resolved` /
  `Won't fix` / `Duplicate`) and a final `## Resolution` section. Map the governed
  `Status:`:
  - **Open** → `Status: active`.
  - **Resolved / Won't fix / Duplicate** → route through `doc-retirer`, which
    **deletes** the report. Promote any specific a reader still needs into the
    architecture or process doc that owns it, repoint inbound references at the
    resolving commit, drop the pointer below, and append a tombstone to
    `docs/context/decisions.md`. Git history keeps the report, so no resolved
    file stays in the tree and there is no resolved index to maintain.
- **Link it (no orphans):** reference every new issue from a governed doc — by
  default an **Open issues** bullet in
  [`docs/context/intent-map.md`](../context/intent-map.md), a Risk in
  [`docs/context/current-state.md`](../context/current-state.md), or the standing
  backlog in [`docs/roadmap.md`](../roadmap.md). This `README` also lists live
  governed issues below, which satisfies the no-orphan rule.
- **Stage + reindex:** under `mode = "git"` a new doc is invisible until
  `git add`ed; stage it, then `docgraph reindex` and `docgraph check --strict` the
  same turn (a new `dangling` blocks completion).
- **Template:** copy `TEMPLATE.md` in this folder. It is index-excluded (a
  top-of-file `<!-- docgraph: ignore -->` marker), so **do not markdown-link to
  it** from a governed doc — the link would dangle. Refer to it by path / inline
  code.

The remaining-work list lives in [`docs/roadmap.md`](../roadmap.md).

The 2026-07-21 cutover decision is
[`docs/decisions/2026-07-21-github-issues-cutover.md`](../decisions/2026-07-21-github-issues-cutover.md).

## Recommended structure

Summary · Impact · Environment/versions · Evidence (reproduction & diagnosis,
with commands/output) · Root-cause hypotheses (ranked) · Defects to fix ·
Recommended next steps · What is NOT broken (scopes the fix) · Resolution.

Lead with the **smallest decisive evidence**, separate **observation** from
**hypothesis**, and always include a **What is NOT broken** section.

## Open issues

- Production typeface training builds a local `TypefaceConfig` and calls `train_typeface` through a cast. `FakeTrainingRunner` covers tests only. [M12 Typeface classifier](2026-07-21-gh-014-m12-typeface-classifier.md). Plan: [M12 plan](../plans/2026-06-10-m12-typeface-classifier.md).
- The production eval worker raises `RuntimeError` in `_build_runner` and never calls `LocalEvalRunner`. The text inside that raise is stale against the currently locked `pdomain-ocr-training` 0.3.0. [M13 Glyph eval slicing](2026-07-21-gh-015-m13-glyph-eval-slicing.md).
- Glyph-classifier kanban still returns `dataset.task_unsupported`. [M14 Glyph classifier](2026-07-21-gh-016-m14-glyph-classifier.md).
- The milestone umbrella stays open until M12–M14 close. [M0–M14 umbrella](2026-07-21-gh-001-milestone-roadmap.md).
- The toast hook is not mounted. The dock polls `GET /api/jobs`. [Jobs surfaces](2026-07-21-gh-025-unify-jobs-surfaces.md).
- Publish workers, the `/settings` banner link, and the dock row target are on the [roadmap](../roadmap.md) and do not have their own issue files.
- `NewRunPage` does not send `device`. The string-to-index mapping is undecided. Plan: [2026-07-14 review fixes](../plans/2026-07-14-review-fixes.md).

Resolved reports are deleted.

Tombstones live in [`docs/context/decisions.md`](../context/decisions.md).
