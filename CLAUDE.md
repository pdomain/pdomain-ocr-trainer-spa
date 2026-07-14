---
Status: active
Owner: CT
Created: 2026-07-14
Last verified: 2026-07-14
Kind: process
---

# pdomain-ocr-trainer-spa

## Agent Index

- **Kind:** process
- **Status:** active
- **Read when:** starting development or selecting repository commands.
- **Search terms:** commands, coding workflow, local development.

Agent guidance for the `pdomain-ocr-trainer-spa` repo.

## Commands

<!-- markdownlint-disable MD013 -->

| target                        | does                                                                                                        |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `make local-setup`            | clone any missing sibling pdomain repos (pdomain-book-tools, pdomain-ops, pdomain-ocr-training, pdomain-ui) |
| `make local-dev`              | switch to local-dev mode (3 Python siblings editable + pdomain-ui linked + marker)                          |
| `make local-check`            | print local-dev mode + per-sibling resolution                                                               |
| `make local-upgrade-deps`     | upgrade deps then restore editables (local-mode only)                                                       |
| `make local-run`              | run the SPA against local-dev workspace (local-mode only)                                                   |
| `make local-setup-py`         | re-apply editable Python siblings (idempotent; called by local-run)                                         |
| `make local-frontend-install` | pnpm install + restore pnpm link overlay for pdomain-ui                                                     |
| `make local-frontend-build`   | Vite build via local-linked siblings (called by local-run)                                                  |
| `make update-pdomain-deps`    | bump pdomain sibling deps to registry latest; leaves diff for review                                        |

<!-- markdownlint-enable MD013 -->

The repository-backed local workflow is defined by the `local-*` Make targets
above and their scripts under `scripts/`. See [DEVELOPMENT.md](DEVELOPMENT.md)
for setup and runtime guidance, [CONVENTIONS.md](CONVENTIONS.md) for coding
rules, and [DOCGRAPH.md](DOCGRAPH.md) for documentation governance.

<!-- workspace-process:start -->

## Before coding

These steps are workspace defaults for any coding task. **User-level settings
override them** — a user's own `~/.claude/CLAUDE.md`, `settings.json`, or a
direct instruction in the conversation takes precedence and may waive or change
any step below.

### Working principles

- **Use skills.** Invoke the relevant superpowers skill before starting —
  process skills first (`brainstorming`, `systematic-debugging`,
  `writing-plans`, `test-driven-development`), then implementation skills. If a
  skill applies, using it is not optional.
- **Write clearly.** Follow `docs/process/writing-style.md` for direct user
  updates, handoffs, final summaries, docs, reports, issue text, PR text, and
  user-facing copy. Keep agent communication short, clear, and easy to scan.
- **Delegate by default.** Dispatch subagents for non-trivial work: per-repo
  agents for repo changes, `Explore` for code searches. This keeps large tool
  output out of the parent context.
- **Parallelize.** Run independent tasks as concurrent subagents — multiple
  agent calls in a single message. Set `model: sonnet` on implementers and
  reviewers.

### Steps

1. **Check the working tree.** `git status --short`. Surface or resolve stray
   uncommitted work before starting — don't build on it.
2. **Read repo guidance.** This repo's `CLAUDE.md` and `CONVENTIONS.md` for
   repo-specific rules.
3. **Consult `docs/` for authoritative context** (whichever folders exist):
   `plans/` (the work plan), `specs/` (design specs — follow any `Spec:` pointer
   from the issue), `research/` (prior investigations), `decisions/` (ADRs /
   constraints), `architecture/` (shipped design).
4. **Check live issue status.** `gh issue view <N> --repo <owner/repo>` —
   confirm it isn't already closed; note its milestone.
5. **Check for in-flight work.** Open PRs and existing branches touching the
   same area, to avoid colliding with work-in-progress.
6. **Consult agent memory.** `.claude/agent-memory/<repo>/feedback_*.md` for
   corrections not yet promoted to `CONVENTIONS.md`.
7. **Locate code with `Explore` first.** Use an `Explore` subagent to find
   relevant files before broad `Read`/grep.
8. **Isolate in a worktree.** Never work directly in the interactive checkout at
   `/workspaces/ocr-container/<repo>/`. Use the `using-git-worktrees` skill to
   set up an isolated worktree. When delegating to a full-power implementation
   agent, pass `isolation: "worktree"` on the `Agent` call (skip for `-docs`
   agents and the `driver` agent). When an agent returns a worktree path +
   branch, use the `finishing-a-development-branch` skill to decide how to
   integrate.
9. **TDD.** Write the failing test first where the plan calls for it.
10. **Verify before committing.** Focused verification plus `make ci`.
11. **Commit locally; do not push** without explicit say-so.

<!-- workspace-process:end -->
