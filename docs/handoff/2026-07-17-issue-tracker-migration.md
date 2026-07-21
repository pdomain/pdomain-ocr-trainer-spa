---
kind: handoff
status: "retired"
created: "2026-07-17"
created_at: "2026-07-17T09:19:17Z"
owner: CT
branch: master
scope: issue-tracker-migration
worktree: /workspaces/pdomain/pdomain-ocr-trainer-spa
base_commit: 81cf25603044b5b374258f6dd546866eef6dd751
supersedes: ""
retired_at: "2026-07-21"
retired_reason: "Cutover executed; open work in docs/roadmap.md and docs/issues/."
---

# Issue tracker migration — pdomain-ocr-trainer-spa (RETIRED)

## Agent Index

- Kind: handoff
- Status: retired
- Read when: auditing how the 2026-07-17 pickup led to the 2026-07-21 cutover.
- Search terms: issue tracker migration, retired handoff, github cutover

## Goal

Clear this repo's GitHub issue tracker into governed docs (roadmap + archive +
`docs/issues/` for evidence-bearing open work).

## Status

**Done on 2026-07-21** (in-tree migration + archive tombstone). Live destinations:

- [docs/roadmap.md](../roadmap.md)
- [docs/issues/](../issues/README.md)
- [cutover decision](../decisions/2026-07-21-github-issues-cutover.md)
- Archive recovery (not in live tree):

  ```bash
  git show b1338d6973b84a5e36060958362fe38e83ba7222:docs/decisions/2026-07-21-github-issues-archive.md
  ```

**Still requires human approval:** permanent `gh issue delete` for all 22
issues (5 open + 17 closed). Do not run deletes until the archive commit is on
the branch you trust.

## Resume steps (remaining)

1. With explicit human go: delete GH issues that still exist for this repo
   (`gh issue delete N --repo pdomain/pdomain-ocr-trainer-spa --yes`).
2. Confirm remote open+closed count is zero.
