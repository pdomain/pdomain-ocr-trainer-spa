---
Status: active
Owner: CT
Created: 2026-07-14
Last verified: 2026-11-13
Kind: context
---

# Shipped behavior and open gaps

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** orienting to shipped behavior, current gaps, and verification.
- **Search terms:** current state, shipped, risks, typeface, jobs, shell.

The repository ships a FastAPI and React 19 OCR trainer.

Present behavior is the architecture set linked from
[trainer workflows](../architecture/trainer-workflows.md), including
[labeler import and freshness](../architecture/labeler-import-and-freshness.md).

Open work is [docs/roadmap.md](../roadmap.md).

Detection and recognition training call `LocalTrainingRunner`.

Typeface training still uses a local config and a cast `train_typeface` call.

The production eval worker raises.

Glyph-classifier kanban returns `dataset.task_unsupported`.

Publish routes validate a request, then raise `AdapterNotImplementedError`.

Quality gates run through the just recipes in
[DEVELOPMENT.md](../../DEVELOPMENT.md).

Releases are local (`scripts/do-release.sh`).

There is no `.github/workflows` tree.

Lint exceptions live in one [catalogue](../conventions/lint-deviations.md).

## Job surfaces and upstream contracts

- **Job progress.** The dock polls `GET /api/jobs`. Run detail uses the job SSE
  stream. `useNotificationStream` is not mounted, so terminal toasts do not
  fire. [Jobs issue](../issues/2026-07-21-gh-025-unify-jobs-surfaces.md).
- **Typeface training, production eval, and publish upload** are not proven by
  seam tests. Typeface training still depends on `train_typeface` existing on
  the typed runner. Production eval raises in `_build_runner` and never calls
  `LocalEvalRunner`. The publish worker is unimplemented in this repo.

## Architecture verification and retirement

The [retirement record](../decisions/2026-11-13-architecture-retirement.md)
tracks the removal of twenty superseded stubs. Architecture now records the
suite identity and preference migration, classification result serialization,
and the current dependency and packaging boundaries. The driver inventory
remains active at `specs/13-driver-contract.md`.

Production typeface training, evaluation and publish are still incomplete.
Neither partial plan was retired. Device mapping, the unmounted toast hook,
and classifier-package scope remain owner decisions in the intent map.
