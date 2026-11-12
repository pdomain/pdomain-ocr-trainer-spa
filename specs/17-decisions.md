---
Status: superseded
Owner: CT
Created: 2026-05-21
Last verified: 2026-11-12
Kind: spec
Promotes to: docs/context/decisions.md
Disposition: Superseded by architecture and the roadmap. Original body is in git history.
---

# 17 — Decisions log

## Agent Index

- **Kind:** spec
- **Status:** superseded
- **Read when:** an old link still names this file.
- **Search terms:** superseded, 17-decisions.md

This file is not current truth. Read [docs/context/decisions.md](../docs/context/decisions.md).

## Adversarial Review

Reviewed against the code on 2026-11-12. This spec had no metadata and no
earlier adversarial review, and the index still called the set the source of
truth.

Durable choices that the code still honors are in the context decisions and the architecture pages. D-T14 (Recharts) was already contradicted. This log is not a second decision register.

The original body was removed in the same change. Recover it from the
parent of the commit that set this file to superseded:
`git log -p -- specs/17-decisions.md`.

## What moved

Shipped behavior is in `docs/context/decisions.md`. Open, deferred, and dropped items are on
[the roadmap](../docs/roadmap.md).
