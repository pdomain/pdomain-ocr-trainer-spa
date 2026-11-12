---
Status: superseded
Owner: CT
Created: 2026-05-21
Last verified: 2026-11-12
Kind: spec
Promotes to: docs/roadmap.md
Disposition: Superseded by architecture and the roadmap. Original body is in git history.
---

# 19 — Deferred glyph classifier

## Agent Index

- **Kind:** spec
- **Status:** superseded
- **Read when:** an old link still names this file.
- **Search terms:** superseded, 19-deferred-glyph-classifier.md

This file is not current truth. Read [docs/roadmap.md](../docs/roadmap.md).

## Adversarial Review

Reviewed against the code on 2026-11-12. This spec had no metadata and no
earlier adversarial review, and the index still called the set the source of
truth.

Glyph kanban is still HTTP 501 `dataset.task_unsupported`. Training defaults and `create_run` return 422 for that task. The classifier contract and eval slicing stay on `pdomain-ocr-training`, as the roadmap says. This repo does not depend on `pdomain-ocr-synth`.

The original body was removed in the same change. Recover it from the
parent of the commit that set this file to superseded:
`git log -p -- specs/19-deferred-glyph-classifier.md`.

## What moved

Shipped behavior is in `docs/roadmap.md`. Open, deferred, and dropped items are on
[the roadmap](../docs/roadmap.md).
