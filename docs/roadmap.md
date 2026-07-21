---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: plan
---

<!-- markdownlint-configure-file { "MD024": { "siblings_only": true } } -->

# pdomain-ocr-trainer-spa Roadmap

## Agent Index

- **Kind:** plan
- **Status:** active
- **Read when:** deciding what to work on next in `pdomain-ocr-trainer-spa`.
- **Search terms:** roadmap, backlog, now next later, open priorities, M12,
  M13, M14, jobs surfaces, typeface, glyph

## Provenance

This roadmap is the standing list of **still-open** work. On 2026-07-21 the
GitHub Issues backlog (5 open, 17 closed) was cut over into governed docs. Tags
like `former GH #NNN` are provenance only. See
[the cutover decision](decisions/2026-07-21-github-issues-cutover.md).

Verbatim former issue bodies (Git history tombstone after the archive is
removed from the live tree):

```bash
git show b1338d6973b84a5e36060958362fe38e83ba7222:docs/decisions/2026-07-21-github-issues-archive.md
```

Authoritative design for milestones remains in `specs/00-19` (especially
`specs/16-milestones.md`). SPA-side M12 plan:
[2026-06-10-m12-typeface-classifier.md](plans/2026-06-10-m12-typeface-classifier.md).

## Goal

Keep a short, honest list of open priorities for the OCR trainer SPA. Prefer
architecture, intent map, and governed issues over a false full backlog.

## Architecture

FastAPI backend + React/Vite TypeScript SPA. Training and evaluation dispatch
through adapters into `pdomain-ocr-training`. Shared shell comes from
`@pdomain/pdomain-ui`. Dataset import and freshness share contracts with the
labeler SPA.

## Tech Stack

Python 3.x with FastAPI and Pydantic; React 19 + TypeScript on Vite; Vitest;
`uv`, pytest, Ruff, basedpyright; ESLint / Prettier / knip for the frontend.

## Global Constraints

Keep reusable training primitives upstream in `pdomain-ocr-training`. Backend
and frontend contracts must stay aligned. Do not claim production typeface or
glyph training until upstream runner contracts exist. Run project CI before
merging.

## Now

- **Jobs surfaces residual** (former GH #25). Dual UX (SSE toasts + AppShell
  jobs dock) is intentional per
  [decisions.md](context/decisions.md) (2026-07-14). Remaining work: document
  roles in architecture, optional SSE-fed dock / quieter toasts.
  Governed issue:
  [unify jobs surfaces](issues/2026-07-21-gh-025-unify-jobs-surfaces.md).

- **Finish typeface production round-trip** (former GH #14 / M12). SPA kanban,
  run creation, and per-class eval UI shipped; remaining gate is upstream
  `TypefaceConfig` + real `train_typeface` / `evaluate_typeface` in
  `pdomain-ocr-training`. Local stub + FakeTrainingRunner remain until then.
  Plan: [M12 typeface classifier](plans/2026-06-10-m12-typeface-classifier.md).

## Next

- **M13 Glyph eval slicing** (former GH #15). Extend eval with
  `GlyphAnnotations`-keyed slices and per-feature metrics rows. Acceptance from
  `specs/07-evaluation-and-metrics.md` §8. Depends on core HF / eval path
  stability (former #13 is closed).

## Later

- **M14 Glyph classifier** (former GH #16). Wire glyph-classifier training from
  `pdomain-ocr-training`, extend run form and eval pages, publish round-trip per
  ROADMAP (g2). Blocked on M13 and upstream glyph training contracts (see
  intent map).

## Blocked / upstream

- **Glyph-classifier training** — needs typed classifier training and config
  contracts in `pdomain-ocr-training` (intent map Blocked).
- **Production typeface train/eval** — SPA seam exists; upstream runner and real
  evaluation contracts do not (intent map Blocked; former GH #14 residual).

## Shipped (compact ledger)

| Former GH | Title | Notes |
| --- | --- | --- |
| #2 | M0 Repo scaffold | Closed 2026-05-21 |
| #3 | M1 Settings + adapters + AppState | Closed 2026-05-21 |
| #4 | M2 Job runner + SSE | Closed 2026-05-21 |
| #5 | M3 Profiles routes + page | Closed 2026-05-21 |
| #6 | M4 Datasets kanban (recognition) | Closed 2026-05-21 |
| #7 | M5 Detection kanban + defaults | Closed 2026-05-21 |
| #8 | M6 Training runs | Closed 2026-05-21 |
| #9 | M7 Models registry + eval | Closed 2026-05-21 |
| #10 | M8 Notifications + a11y polish | Closed 2026-05-21 |
| #11 | M9 Driver contract + cutover prep | Closed 2026-05-21 |
| #12 | M10 HF read path | Closed 2026-05-22 |
| #13 | M11 HF publish path | Closed 2026-05-22 |
| #17 | [nightly] slow tests 2026-05-22 | Transient CI; closed |
| #18 | SPDX allowlist from book-tools | Closed 2026-05-22 |
| #19 | Frontend tsc errors on main | Closed 2026-05-22 |
| #21 | [nightly] slow tests 2026-05-23 | Transient CI; closed |
| #24 | Re-enable downgraded ESLint rules | Closed 2026-06-10; residual may live under lint catalogue |

Former GH #1 was the umbrella M0–M14 tracking issue. Open legs of that plan are
the Now / Next / Later items above; closed legs are this ledger.
