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
| #1 | M0–M14 umbrella roadmap | [`docs/roadmap.md`](../roadmap.md) (standing plan + shipped ledger) |
| #14 | M12 Typeface classifier | Roadmap **Now** (SPA shipped; upstream gate) |
| #15 | M13 Glyph eval slicing | Roadmap **Next** |
| #16 | M14 Glyph classifier | Roadmap **Later** / intent map Blocked |
| #25 | Unify jobs surfaces | Roadmap **Now** + governed issue report |

Closed set (#2–#13, #17–#19, #21, #24): completed milestones, short-lived CI
noise, and finished chores. Bodies were archived into
`docs/decisions/2026-07-21-github-issues-archive.md` for a Git history
tombstone, then removed from the live tree in a follow-up commit.

A 2026-07-17 handoff
([issue-tracker-migration](../handoff/2026-07-17-issue-tracker-migration.md))
described the procedure; this cutover executes it against the sibling pattern
used by `pdomain-ocr-cli` and `pdomain-ocr-simple-gui`.

## Decision

1. **Keep the GitHub Issues feature enabled** and drive the remote issue count
   to **zero** after the archive commit exists and a human approves deletion.
2. **Treat `docs/roadmap.md` as the standing backlog** for open product and
   milestone work. Tags like `former GH #25` are provenance only.
3. **Use `docs/issues/`** only for governed, evidence-bearing bug and
   investigation reports (template: `docs/issues/TEMPLATE.md`). At cutover only
   former #25 meets that bar among open items.
4. **Do not file routine backlog on GitHub Issues** for this repo. If one is
   filed by mistake, move it into the roadmap or a governed report and delete
   the GitHub issue—or keep it only after an owner decision to resume GitHub
   tracking.
5. **Recover archived text** with:

   ```bash
   git show <archive-add-sha>:docs/decisions/2026-07-21-github-issues-archive.md
   ```

   Replace `<archive-add-sha>` with the commit that added the archive file
   (recorded in the tombstone commit message).

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
| #1, #14–#16, #25 | open | [`docs/roadmap.md`](../roadmap.md); #25 also [`docs/issues/2026-07-21-gh-025-unify-jobs-surfaces.md`](../issues/2026-07-21-gh-025-unify-jobs-surfaces.md) |
| #2–#13, #17–#19, #21, #24 | closed | Shipped rows in roadmap + full bodies in archive tombstone |
