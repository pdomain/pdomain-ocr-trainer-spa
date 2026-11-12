---
Status: superseded
Owner: CT
Created: 2026-05-21
Last verified: 2026-11-12
Kind: spec
Promotes to: docs/architecture/trainer-workflows.md
Disposition: Superseded by architecture and the roadmap. Original body is in git history.
---

# 00 — Overview

## Agent Index

- **Kind:** spec
- **Status:** superseded
- **Read when:** an old link still names this file.
- **Search terms:** superseded, 00-overview.md

This file is not current truth. Read [docs/architecture/trainer-workflows.md](../docs/architecture/trainer-workflows.md).

## Adversarial Review

Reviewed against the code on 2026-11-12. This spec had no metadata and no
earlier adversarial review, and the index still called the set the source of
truth.

The overview still named Recharts, a generated TypeScript client, GitHub Actions, and a single live-progress path. The code uses an SVG chart, hand-written clients, a local release script, a polling jobs dock, and a separate run-detail SSE stream.

The original body was removed in the same change. Recover it from the
parent of the commit that set this file to superseded:
`git log -p -- specs/00-overview.md`.

## What moved

Shipped behavior is in `docs/architecture/trainer-workflows.md`. Open, deferred, and dropped items are on
[the roadmap](../docs/roadmap.md).
