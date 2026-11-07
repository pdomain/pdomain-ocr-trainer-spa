---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-06
Kind: plan
---

# Remaining work

## Agent Index

- **Kind:** plan
- **Status:** active
- **Read when:** deciding what to work on next in `pdomain-ocr-trainer-spa`.
- **Search terms:** roadmap, remaining work, typeface, glyph eval, glyph
  classifier, jobs dock, device index

Open work is the list in Goal.

Shipped behavior is the Architecture links.

## Goal

- Production typeface training still builds a local `TypefaceConfig` and calls
  `train_typeface` on a cast runner. `FakeTrainingRunner` covers tests.
  [M12 plan](plans/2026-06-10-m12-typeface-classifier.md).
  [M12 issue](issues/2026-07-21-gh-014-m12-typeface-classifier.md).
- The production eval worker raises `RuntimeError`. The message names missing
  glyph-annotation input and hard-coded empty slices.
  [M13 issue](issues/2026-07-21-gh-015-m13-glyph-eval-slicing.md).
- Glyph-classifier kanban still returns `dataset.task_unsupported`, HTTP 501.
  [M14 issue](issues/2026-07-21-gh-016-m14-glyph-classifier.md).
- The M0–M14 umbrella stays open until M12, M13, and M14 close.
  [Umbrella issue](issues/2026-07-21-gh-001-milestone-roadmap.md).
- Job toasts and the jobs dock both stay. An SSE-fed dock and quieter toasts
  are not built. Job toasts use the notification stream. The jobs dock polls
  `GET /api/jobs`.
  [Jobs issue](issues/2026-07-21-gh-025-unify-jobs-surfaces.md).
- `NewRunPage` still does not send `device`. The suite stores a device string.
  `CreateRunRequest.device` is an optional integer. That mapping is undecided.
  Suite mount, the settings link, and chord shortcuts from the 2026-07-14
  review are already fixed.
  [Review-fixes plan](plans/2026-07-14-review-fixes.md).

## Architecture

- [Trainer workflows](architecture/trainer-workflows.md)
- [Labeler import and freshness](architecture/labeler-import-and-freshness.md)

## Tech Stack

Python with FastAPI and a React 19 TypeScript SPA.

Commands are in [DEVELOPMENT.md](../DEVELOPMENT.md).

## Global Constraints

- Do not treat seam tests as proof of production typeface training or production
  eval.
- Do not add a third job-progress surface.
- Do not invent the run-form device mapping before an owner decides it.
