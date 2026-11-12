---
Status: superseded
Owner: CT
Created: 2026-05-21
Last verified: 2026-11-12
Kind: spec
Promotes to: docs/architecture/runs-and-evaluation.md
Disposition: Superseded by architecture and the roadmap. Original body is in git history.
---

# 07 — Evaluation and metrics

## Agent Index

- **Kind:** spec
- **Status:** superseded
- **Read when:** an old link still names this file.
- **Search terms:** superseded, 07-evaluation-and-metrics.md

This file is not current truth. Read [docs/architecture/runs-and-evaluation.md](../docs/architecture/runs-and-evaluation.md).

## Adversarial Review

Reviewed against the code on 2026-11-12. This spec had no metadata and no
earlier adversarial review, and the index still called the set the source of
truth.

Eval routes and the form exist. worker/evaluate.py _build_runner raises. Glyph-slice acceptance is on the roadmap. Compare query params are not read.

The original body was removed in the same change. Recover it from the
parent of the commit that set this file to superseded:
`git log -p -- specs/07-evaluation-and-metrics.md`.

## What moved

Shipped behavior is in `docs/architecture/runs-and-evaluation.md`. Open, deferred, and dropped items are on
[the roadmap](../docs/roadmap.md).
