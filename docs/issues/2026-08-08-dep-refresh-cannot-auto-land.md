---
Status: active
Owner: CT
Created: 2026-08-08
Last verified: 2026-08-08
Kind: issue
Level: I1
---

# dep-refresh cannot auto-land: dated branches will accumulate once the workflow runs

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-08-08
- **Resolution:** Open
- **Severity:** Medium — latent branch-accumulation risk, not yet triggered
  (`dep-refresh` shows zero runs to date; this is preventive, not cleanup of an
  observed pile-up)
- **Affected version:** pdomain-ocr-trainer-spa master @ `0a70741483b0`
  (`.github/workflows/dep-refresh.yml` @ `7772cad8dbf3`)
- **Read when:** touching `.github/workflows/dep-refresh.yml`, branch
  protection on `master`, or auto-merge/dep-refresh automation in this repo.
- **Search terms:** dep-refresh, dated branch, delete_branch_on_merge,
  auto-merge, branch protection, required status checks, repo rename, stray
  branches.
- **Relates to:** `pdomain-ui` repo, `docs/specs/2026-07-16-dep-refresh-auto-land-design.md`
  (dep-refresh auto-land design spec; authority repo, read-only reference —
  not linked, lives outside this repo's docgraph index)

## Summary

`.github/workflows/dep-refresh.yml` names a fresh branch per run
(`dep-refresh/$(date +%Y-%m-%d)-$GITHUB_RUN_ID`) and the repo has
`delete_branch_on_merge: false`. Nothing ever reuses or cleans up a prior
run's branch or pull request. This is the same structural design that let
stray `dep-refresh` branches and pull requests pile up in sibling repos.

This repo currently shows **zero** stray `dep-refresh` branches and **zero**
dep-refresh pull requests — but that is because the workflow has **never
executed**, not because anyone cleaned up after it. `gh api
.../actions/workflows/<id>/runs --jq '.total_count'` returns `0`. The
structural defect is present and will start accumulating branches/PRs the
first time the workflow runs, exactly as it did in the peers this report is
modeled on. This report is preventive.

Separately, this repo underwent a `main` → `master` default-branch rename
(evidenced by a `CreateEvent`/`DeleteEvent` pair on 2026-07-12 and the last
`main`-targeted CI run predating it). Two peer repos (`pdomain-ops`,
`pdomain-ocr-training`) have a required branch-protection status check left
over from a pre-rename job name that no job now produces, silently blocking
every pull request. **This repo does not have that problem**: the sole
required context is `ci`, and `.github/workflows/ci.yml` has exactly one job,
`id: ci` / `name: ci`, whose reported check is literally `ci`. The gate is
correctly wired.

## Impact

- No pull requests or branches are affected today — the automation has not
  yet fired.
- Once `dep-refresh` runs (weekly cron, Sundays 02:00 UTC, or manual
  `workflow_dispatch`), every run that produces a diff will create a new
  dated branch and a new PR. A red week leaves its branch and PR behind
  permanently (no auto-cleanup), and `delete_branch_on_merge: false` means
  even a **green**, auto-merged week leaves its branch behind. Branches and
  PRs accumulate one per run with no reuse.
- No pull request has exercised the `master` branch protection gate since the
  `main` → `master` rename on 2026-07-12 — all commits since then landed via
  direct push, not through a PR. The `ci` required-context wiring is
  structurally correct (job name matches required context) but is untested by
  an actual PR post-rename.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-trainer-spa
default branch: master
workflow: .github/workflows/dep-refresh.yml (added 2026-05-31, commit 6053c1d;
          last touched 2026-07-12, commit 7772cad — same commit as the rename)
gate workflow: .github/workflows/ci.yml
gh CLI: authenticated against github.com
```

## Evidence

### 1. `dep-refresh` has never run — zero runs, not zero survivors

```text
$ gh workflow list --repo pdomain/pdomain-ocr-trainer-spa --all
ci             active  280973055
dep-refresh    active  286365141
nightly        active  280973059
release        active  280973063
Dependency Graph active 311646547

$ gh api repos/pdomain/pdomain-ocr-trainer-spa/actions/workflows/286365141/runs --jq '.total_count'
0

$ gh run list --repo pdomain/pdomain-ocr-trainer-spa --workflow dep-refresh.yml --limit 10
(empty)
```

The workflow is registered and active but has produced zero runs since it was
added on 2026-05-31 (commit `6053c1d`) — roughly ten weekly cron windows have
passed. Neither the schedule nor a manual `workflow_dispatch` has fired it.
This proves the observed zero-branches/zero-PRs state is an absence of
activity, not a successful cleanup.

### 2. Zero stray branches and zero dep-refresh PRs, corroborating (1)

```text
$ gh api repos/pdomain/pdomain-ocr-trainer-spa/branches --jq '.[].name'
master

$ git ls-remote origin 'refs/heads/dep-refresh*'
(empty)

$ gh pr list --repo pdomain/pdomain-ocr-trainer-spa --state all --search "dep refresh" --limit 20
(empty)

$ gh pr list --repo pdomain/pdomain-ocr-trainer-spa --state all --limit 30 \
    --json number,state,createdAt,mergedAt,baseRefName
23  MERGED  2026-05-23T19:25:17Z  2026-05-23T19:26:39Z  main
22  MERGED  2026-05-23T18:48:20Z  2026-05-23T18:50:57Z  main
20  MERGED  2026-05-22T23:26:29Z  2026-05-22T23:29:25Z  main
```

`master` is the only branch in the repo. The only PRs on record — numbers 20,
22, and 23 — predate the rename, targeted `main`, and are unrelated to
dep-refresh. There is no evidence of manual cleanup — there is nothing to
have cleaned up.

### 3. The workflow's own structure guarantees accumulation once it runs

```yaml
BRANCH="dep-refresh/$(date +%Y-%m-%d)-$GITHUB_RUN_ID"
...
git checkout -b "$BRANCH"
...
gh pr create --title "chore: weekly dep refresh" ... --head "$BRANCH" ...
gh pr merge --auto --rebase
```

(`.github/workflows/dep-refresh.yml`, "Create branch, commit, and open PR"
step.) Every run mints a brand-new branch name; nothing checks for or reuses
a prior run's branch or open PR.

```text
$ gh api repos/pdomain/pdomain-ocr-trainer-spa --jq '.delete_branch_on_merge'
false
```

Even a fully green, auto-merged run leaves its branch behind because
`delete_branch_on_merge` is `false`. This is the identical design the
`pdomain-ui` repo's `docs/specs/2026-07-16-dep-refresh-auto-land-design.md`
(§2, "Bug 2 — failing refreshes accumulate") documents as the root cause of
seven-branch pile-ups in peer repos, once those repos' workflows actually ran
repeatedly.

### 4. The `master` merge gate itself is sound — no leftover-check mismatch from the rename

```text
$ gh api repos/pdomain/pdomain-ocr-trainer-spa/branches/master/protection \
    --jq '.required_status_checks.contexts'
["ci"]
```

```yaml
# .github/workflows/ci.yml
on:
  pull_request:
    branches: [master]
jobs:
  ci:
    name: ci
    ...
```

The single required context, `ci`, is produced by the single job in
`ci.yml`, whose job id and `name:` are both `ci`. Confirmed against real
history — every merged PR that ran this gate reported exactly that context:

```text
$ gh pr list --repo pdomain/pdomain-ocr-trainer-spa --state merged --limit 3 \
    --json number,statusCheckRollup --jq '.[] | {number, checks:[.statusCheckRollup[]?.context]}'
{"number":23,"checks":["ci"]}
{"number":22,"checks":["ci"]}
{"number":20,"checks":["ci"]}
```

Unlike `pdomain-ops` and `pdomain-ocr-training` — where branch protection
still requires a pre-rename context no current job produces, silently
blocking every PR — this repo has only one required context and it matches
the one job that exists. No pull request has exercised this gate since the
`main` → `master` rename (all three merges above predate it and targeted
`main`), so the wiring is structurally sound but not freshly proven by a live
PR.

### 5. The rename itself, for the record

```text
$ gh api repos/pdomain/pdomain-ocr-trainer-spa --jq '.default_branch'
master

$ gh api repos/pdomain/pdomain-ocr-trainer-spa/events --jq '.[] | {type,created_at}'
...
{"type":"CreateEvent","created_at":"2026-07-12T10:09:01Z"}
{"type":"DeleteEvent","created_at":"2026-07-12T10:10:01Z"}
...
```

The last CI run against `main` was 2026-05-26; branch protection and
`ci.yml`/`dep-refresh.yml` (`--base master`) already reference `master`. The
`CreateEvent`/`DeleteEvent` pair on 2026-07-12 lines up with a `main` →
`master` branch rename that commit `7772cad` (which also last touched
`dep-refresh.yml`) appears to correspond to.

## Root-cause hypotheses

1. **(Confirmed) Per-run dated branch name + `delete_branch_on_merge: false`**
   — `.github/workflows/dep-refresh.yml` names each run's branch with the
   date and run id and never reuses or deletes it; the repo setting means
   even successful auto-merges leave branches behind. This is a design
   defect, directly verified by reading the workflow file and the repo
   setting (evidence §3). It has not yet produced any branches only because
   the workflow has never run (evidence §1–2).
2. **Not a factor here: stale required-check context from the rename** — the
   pattern that blocks every PR in `pdomain-ops` and `pdomain-ocr-training`.
   Verified absent in this repo: the single required context (`ci`) is
   produced by the single job that exists (evidence §4).

## Defects to fix

1. **Dated per-run branch, no reuse** — `dep-refresh.yml` should force-push a
   single reusable `dep-refresh` branch from fresh `master`, open a PR only
   when no open one exists, and re-arm `gh pr merge --auto --rebase`, per the
   `pdomain-ui` design spec, §"B. One reusable branch (`dep-refresh.yml`)"
   (`pdomain-ui` repo, `docs/specs/2026-07-16-dep-refresh-auto-land-design.md`).
   (Primary)
2. **`delete_branch_on_merge: false`** — set to `true` on this repo so a
   green auto-merge removes the reusable branch, per the same spec, §"C.
   Enable delete-on-merge (repo setting)".

## Next steps

1. Apply the `pdomain-ui` dep-refresh auto-land design
   (`pdomain-ui` repo, `docs/specs/2026-07-16-dep-refresh-auto-land-design.md`)
   to this repo: reusable `dep-refresh` branch (force-pushed from fresh
   `master` each run), open-PR-only-if-none-open guard, re-armed
   `gh pr merge --auto --rebase`, and `delete_branch_on_merge: true`.
2. Because this repo's `ci` required-check wiring already matches its job
   (evidence §4), this repo does not need the `pdomain-ui` spec's Bug-1 fix
   (the `unit-test` aggregation job) — confirm that stays true if `ci.yml`'s
   job structure changes.
3. After landing the fix, trigger `workflow_dispatch` once manually to
   observe a full green cycle (branch created, PR opened, gate passes,
   auto-merge lands, branch deleted) before relying on the weekly cron.

## What is NOT broken

- The `master` branch protection required-status-check wiring: `ci` (context)
  matches `ci` (job), unlike the two peer repos with a rename-orphaned
  required context.
- Repository branch state: no stray branches exist today.
- The dep-refresh workflow's dependency-upgrade logic itself (Python via
  `make upgrade-deps`, frontend via `pnpm update`, Actions SHA pin refresh)
  — this report only concerns branch/PR lifecycle, not what gets upgraded.

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the `docs/issues/README.md` pointer to Resolved,
and route retirement through `doc-retirer`.
