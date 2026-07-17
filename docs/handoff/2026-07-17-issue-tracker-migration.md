---
kind: handoff
status: "active"
created: "2026-07-17"
created_at: "2026-07-17T09:19:17Z"
owner: CT
branch: master
scope: issue-tracker-migration
worktree: /workspaces/pdomain/pdomain-ocr-trainer-spa
base_commit: 81cf25603044b5b374258f6dd546866eef6dd751
supersedes: ""
---

# Issue tracker migration — pdomain-ocr-trainer-spa

## Agent Index

- Kind: handoff
- Status: active
- Read when: you are about to migrate this repo's GitHub issue tracker into
  `docs/`, or you are asked to clear/archive/close out issues in
  `pdomain/pdomain-ocr-trainer-spa`.
- Search terms: issue tracker migration, roadmap, archive closed issues,
  gh issue delete, docs/roadmap.md, closed-issue-archive-pattern

## Goal

Clear this repo's GitHub issue tracker the same way it was already cleared
for `pdomain-ocr-cli` (50 issues) and `pdomain-ocr-simple-gui` (37 issues,
roadmap-first). Concretely:

1. Migrate the open backlog into `docs/roadmap.md` so no pending work is lost
   when issues go away.
2. Archive every in-scope issue's full text (title, metadata, body, all
   comments) into Git history via a decision doc, then delete that doc in a
   follow-up commit — the commit history becomes the permanent record.
3. Delete the issues from GitHub once the archive commit is in place.

This handoff does **not** perform the migration. It is the pickup prompt for
the session that will.

## Current state

As of the investigation for this handoff (2026-07-17):

- **Open issues: 5**
- **Closed issues: 17**
- `docs/decisions/` exists (currently empty).
- No `docs/roadmap.md` yet.
- No `docs/handoff/` directory existed before this file (this handoff creates
  it).
- Docgraph is present (`DOCGRAPH.md` at repo root).
- Admin access on the repo is confirmed (needed for `gh issue delete`).
- Working tree was clean at investigation time.

### Label breakdown (open issues)

- `kind:feature` + `status:backlog`: 3 issues (#16, #15, #14)
- `kind:spec` + `status:backlog`: 1 issue (#1)
- No labels: 1 issue (#25)

No `priority:*` or `area:*` labels are in use on the open set.

### The 5 open issues

- **#25 — Unify jobs surfaces: useNotificationStream toasts vs AppShell jobs
  dock** (no labels). Body: a follow-on from the pdomain-ui adoption work
  (Track A, Milestone F). After the AppShell migration, two job-progress
  surfaces coexist — `useNotificationStream` (SSE toasts, pre-existing) and
  `useTrainerJobs` (polling hook feeding the AppShell jobs dock, new). A
  decision is needed: retire the toasts, feed SSE into the dock instead of
  polling, or keep both deliberately. Explicitly scoped out of Track A on
  purpose — real, unresolved backlog.
- **#16 — M14 Glyph classifier** (`kind:feature`, `status:backlog`).
- **#15 — M13 Glyph eval slicing** (`kind:feature`, `status:backlog`).
- **#14 — M12 Typeface classifier** (`kind:feature`, `status:backlog`).
- **#1 — pd-ocr-trainer-spa milestone roadmap (M0-M14)** (`kind:spec`,
  `status:backlog`). Tracking spec for the whole implementation roadmap:
  the FastAPI + React/Vite/TS replacement for the legacy `pd-ocr-trainer`
  NiceGUI UI. 15 milestones (M0-M14) — M0-M3 infrastructure, M4-M9 vertical
  slices to core parity, M10-M14 post-core-parity roadmap milestones.
  Authoritative design lives in specs 00-19. Points at
  `docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md`.

**Read on whether these are real pending work:** yes. All 5 are genuine,
unfinished backlog, not stale or already-superseded issues. Issue number 1
is the umbrella tracking issue for the whole M0-M14 milestone plan. Issue
numbers 14, 15, and 16 are three of its still-open milestones (M12-M14,
the post-core-parity tail). Issue number 25 is a real unresolved design
decision surfaced by completed work. None of the 5 look safe to drop
silently: they must be carried into `docs/roadmap.md` before the tracker
is cleared.

## Decisions

- **Scope**: migrate the 5 **open** issues (recommended). The 17 **closed**
  issues are completed history — archiving them into the decision-doc/Git
  pattern is **optional**, only worth doing for a full tracker wipe. Do not
  feel obligated to touch the closed issues if the open-issue migration is
  the actual goal.
- **Roadmap-first is required**: because the 5 open issues represent real,
  unfinished backlog (see above), do not delete any of them without first
  carrying their content into `docs/roadmap.md`. Never delete open work
  without a roadmap landing spot.
- With only 5 open issues, a lightweight roadmap document is sufficient —
  no need to over-engineer structure beyond what `pdomain-ocr-cli`'s roadmap
  already demonstrates.

## The proven procedure

This is the same procedure already used successfully in `pdomain-ocr-cli`
and `pdomain-ocr-simple-gui`. Follow it in order; each step gates the next.

1. **Pull each in-scope issue's full record.** For every issue being
   migrated (at minimum the 5 open ones):

   ```bash
   gh issue view N --repo pdomain/pdomain-ocr-trainer-spa \
     --json number,title,author,createdAt,closedAt,state,stateReason,labels,body,comments,url
   ```

   Save the output to a scratch file and `sha256sum` it, so the archive step
   below can be checked against a known-good snapshot.

2. **Author `docs/roadmap.md`.** Mirror the structure of
   `../pdomain-ocr-cli/docs/roadmap.md` (now/next/later style). Tag every
   migrated item with its original issue number, e.g. `#25`, `#16`, so the
   provenance trail back to the archived issue is traceable from the
   roadmap.

3. **Render the archive decision doc**, e.g.
   `docs/decisions/2026-07-DD-closed-issues-archive.md` (or an
   open-issues-specific name if scope is open-only — pick a name that
   matches what was actually archived). Structure:
   - Docgraph frontmatter: `kind: decision`, `status: retired`.
   - An `## Agent Index` section per docgraph convention.
   - `Context` / `Decision` / `Consequences` / `Supersedes` sections.
   - Add `<!-- markdownlint-disable -->` immediately after the frontmatter
     block — the verbatim issue bodies/comments below it will not conform to
     markdownlint rules.
   - Then one `## #N — <title>` section per archived issue, each containing
     its full metadata (author, created/closed dates, state, labels, url)
     followed by the complete body and all comments, verbatim.

4. **Commit the roadmap and the archive doc together**, then `git rm` the
   archive doc in a **second, separate commit** whose message cites the SHA
   of the add commit (so the tombstone commit message says "content lives at
   `git show <add-sha>:<path>`"). Git history is the permanent record; the
   live `docs/` tree does not carry the verbatim issue dump going forward —
   only `docs/roadmap.md` stays live.

5. **Delete the issues from GitHub only after the archive commit exists**:

   ```bash
   gh issue delete N --repo pdomain/pdomain-ocr-trainer-spa --yes
   ```

   This is **permanent** — GitHub does not support undeleting issues. Get an
   explicit human "go" before running any `gh issue delete` command, even
   though admin access is already confirmed.

## Gotchas

- `pre-commit-update` may bump `.pre-commit-config.yaml` as a side effect of
  running the hooks and abort the commit. If that happens: revert the
  config file (`git checkout -- .pre-commit-config.yaml`) and retry the
  commit with `SKIP=pre-commit-update git commit ...`.
- Validate new/edited docs with the `markdownlint` hook and the docgraph
  check MCP tool before committing. An "orphan doc" advisory from docgraph
  on the archive doc is expected and fine — it is intentionally retired
  immediately after landing.

## Pointers

- `docs/roadmap.md` — does not exist yet; to be created by this migration.
- `docs/decisions/` — exists, currently empty; the archive doc lands here.
- `DOCGRAPH.md` — repo's docgraph configuration/entry point.
- `../pdomain-ocr-cli/docs/roadmap.md` — worked example of the target
  roadmap shape (50-issue migration).
- `../pdomain-ocr-simple-gui/docs/roadmap.md` — worked example of the
  roadmap-first pattern (37-issue migration).

## Reference worked examples

- `pdomain-ocr-cli` archive commit: `9498407`.
- `pdomain-ocr-simple-gui` archive-add commit: `ec3979f`, followed by the
  archive-remove (tombstone) commit: `7f3be6b`.
- Agent memory pattern name to search for: `closed-issue-archive-pattern`.

## Resume steps

1. `gh issue view 1 --repo pdomain/pdomain-ocr-trainer-spa --json number,title,author,createdAt,closedAt,state,stateReason,labels,body,comments,url`
   (repeat for #14, #15, #16, #25 — save each to scratch and `sha256sum` it).
2. Read `../pdomain-ocr-cli/docs/roadmap.md` and
   `../pdomain-ocr-simple-gui/docs/roadmap.md` to confirm the target shape
   before drafting this repo's `docs/roadmap.md`.
3. Draft `docs/roadmap.md` covering all 5 open issues, tagging each with its
   `#N`, then proceed to step 3 of "The proven procedure" above.
