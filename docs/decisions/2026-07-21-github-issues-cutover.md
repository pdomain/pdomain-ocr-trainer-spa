---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: decision
---

# GitHub Issues cutover to governed docs

## Agent Index

- **Kind:** decision
- **Status:** active
- **Read when:** tracing a former GitHub issue number, confirming the tracker is
  empty, or checking what the cutover preserved and what it skipped.
- **Search terms:** GitHub issues cutover, migration, delete issues, tombstone,
  former GH, issue archive, docs/issues, roadmap

This repository does not use GitHub Issues for planning. Open work lives in
[`docs/roadmap.md`](../roadmap.md). Evidence-bearing defects use
[`docs/issues/`](../issues/README.md). The GitHub Issues **feature stays
enabled** so the repo can accept issues later if needed, but the remote tracker
is intended to hold **zero** issues after deletion. Former issue text is
recoverable from Git history only.

## Context

Through mid-July 2026 this repository tracked trainer SPA work in GitHub Issues
under `pdomain/pdomain-ocr-trainer-spa`. At cutover investigation time there
were **5 open** and **17 closed** issues.

Open set:

| Former GH | Title | Cutover destination |
| --- | --- | --- |
| #1 | M0–M14 umbrella roadmap | [issue file](../issues/2026-07-21-gh-001-milestone-roadmap.md) + roadmap |
| #14 | M12 Typeface classifier | [issue file](../issues/2026-07-21-gh-014-m12-typeface-classifier.md) + roadmap Now |
| #15 | M13 Glyph eval slicing | [issue file](../issues/2026-07-21-gh-015-m13-glyph-eval-slicing.md) + roadmap Next |
| #16 | M14 Glyph classifier | [issue file](../issues/2026-07-21-gh-016-m14-glyph-classifier.md) + roadmap Later |
| #25 | Unify jobs surfaces | [issue file](../issues/2026-07-21-gh-025-unify-jobs-surfaces.md) + roadmap Now |

Closed set (#2–#13, #17–#19, #21, #24): completed milestones, short-lived CI
noise, and finished chores. Bodies were archived into
`docs/decisions/2026-07-21-github-issues-archive.md` for a Git history
tombstone, then removed from the live tree in a follow-up commit.

A 2026-07-17 handoff
([issue-tracker-migration](../handoff/2026-07-17-issue-tracker-migration.md))
described the procedure; this cutover executes it against the sibling pattern
used by `pdomain-ocr-cli` and `pdomain-ocr-simple-gui`.

## Decision

1. **Keep the GitHub Issues feature enabled** and keep the remote issue count
   at **zero**. On 2026-07-21, after archive + human approval, all 22 issues
   were permanently deleted (`gh issue list --state all` → 0).
2. **Treat `docs/roadmap.md` as the standing backlog** for open product and
   milestone work. Tags like `former GH #25` are provenance only.
3. **Use `docs/issues/`** for governed issue reports (template:
   `docs/issues/TEMPLATE.md`). **Every open** former GitHub issue has an
   individual file (#1, #14, #15, #16, #25). Closed issues are not recreated as
   live files; they remain in the archive tombstone and the roadmap shipped
   ledger.
4. **Do not file routine backlog on GitHub Issues** for this repo. If one is
   filed by mistake, move it into the roadmap or a governed report and delete
   the GitHub issue—or keep it only after an owner decision to resume GitHub
   tracking.
5. **Recover archived text** with:

   ```bash
   git show b1338d6973b84a5e36060958362fe38e83ba7222:docs/decisions/2026-07-21-github-issues-archive.md
   ```

   That SHA is the archive-add commit (also named in the tombstone commit
   message).

## Consequences

- Former issue URLs under
  `github.com/pdomain/pdomain-ocr-trainer-spa/issues/N` will stop resolving once
  issues are deleted (not merely closed).
- Agents and humans plan from the roadmap, intent map, architecture docs, and
  governed issue reports.
- Milestone design remains in `specs/` and plans; the cutover does not rewrite
  those sources.
- The Issues tab can appear empty; that is intentional after deletion.

## Supersedes / Superseded-by

Supersedes the populated GitHub Issues backlog for this repository. Does not
supersede `docs/roadmap.md`, `specs/`, or architecture docs.

## Completed-issue ledger (compact)

| Former GH | State at cutover | Local destination |
| --- | --- | --- |
| #1 | open | [gh-001](../issues/2026-07-21-gh-001-milestone-roadmap.md) + roadmap umbrella |
| #14 | open | [gh-014](../issues/2026-07-21-gh-014-m12-typeface-classifier.md) + roadmap Now |
| #15 | open | [gh-015](../issues/2026-07-21-gh-015-m13-glyph-eval-slicing.md) + roadmap Next |
| #16 | open | [gh-016](../issues/2026-07-21-gh-016-m14-glyph-classifier.md) + roadmap Later |
| #25 | open | [gh-025](../issues/2026-07-21-gh-025-unify-jobs-surfaces.md) + roadmap Now |
| #2–#13, #17–#19, #21, #24 | closed | Shipped rows in roadmap + full bodies in archive tombstone |
