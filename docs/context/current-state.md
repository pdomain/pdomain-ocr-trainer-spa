---
Status: active
Owner: CT
Created: 2026-07-14
Last verified: 2026-07-14
Kind: context
---

# Current state

## Agent Index

- **Kind:** context
- **Status:** active
- **Read when:** orienting to shipped behavior, current gaps, and verification.
- **Search terms:** current state, shipped, risks, typeface, jobs, shell.

The repository ships a FastAPI and React 19 OCR trainer with profile, dataset,
training-run, evaluation, model, Hugging Face, labeler-freshness, and shared
shell workflows. [Trainer workflows](../architecture/trainer-workflows.md) and
[labeler import and freshness](../architecture/labeler-import-and-freshness.md)
record the present architecture.

The main incomplete production path is typeface training and evaluation. The
dataset API, browser route, and seam tests exist, but those tests do not prove a
real upstream `train_typeface` or evaluation round-trip. Glyph-classifier
training is also blocked on upstream contracts.

Repository quality gates use Ruff, basedpyright, Vitest, TypeScript, ESLint,
Prettier, knip, pytest, browser tests, frontend build, and package builds
through the Make targets in [DEVELOPMENT.md](../../DEVELOPMENT.md). Intentional
static analysis exceptions live in one
[catalogue](../conventions/lint-deviations.md).
