---
Status: active
Owner: CT
Created: 2026-07-14
Last verified: 2026-11-06
Kind: context
---

# Shipped behavior and open gaps

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** orienting to shipped behavior, current gaps, and verification.
- **Search terms:** current state, shipped, risks, typeface, jobs, shell.

The repository ships a FastAPI and React 19 OCR trainer.

Present behavior is
[trainer workflows](../architecture/trainer-workflows.md) and
[labeler import and freshness](../architecture/labeler-import-and-freshness.md).

Open work is the short list in [docs/roadmap.md](../roadmap.md).

Detection and recognition training call `LocalTrainingRunner`.

Typeface training still uses a local config and a cast `train_typeface` call.

The production eval worker raises.

Glyph-classifier kanban returns `dataset.task_unsupported`.

Quality gates run through the Make targets in
[DEVELOPMENT.md](../../DEVELOPMENT.md).

Releases are local (`scripts/do-release.sh`).

There is no `.github/workflows` tree.

Lint exceptions live in one [catalogue](../conventions/lint-deviations.md).

## Job surfaces and upstream contracts

- **Two job surfaces.** The split is intentional. An SSE-fed dock is not built.
  Toasts follow the notification stream. The dock polls `GET /api/jobs`.
  [Jobs issue](../issues/2026-07-21-gh-025-unify-jobs-surfaces.md).
- **Typeface training and production eval** still depend on upstream contracts.
  SPA seam tests are not that proof.
