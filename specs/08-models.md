---
Status: superseded
Owner: CT
Created: 2026-05-21
Last verified: 2026-11-12
Kind: spec
Promotes to: docs/architecture/profiles-datasets-and-models.md
Disposition: Superseded by architecture and the roadmap. Original body is in git history.
---

# 08 — Models

## Agent Index

- **Kind:** spec
- **Status:** superseded
- **Read when:** an old link still names this file.
- **Search terms:** superseded, 08-models.md

This file is not current truth. Read [docs/architecture/profiles-datasets-and-models.md](../docs/architecture/profiles-datasets-and-models.md).

## Adversarial Review

Reviewed against the code on 2026-11-12. This spec had no metadata and no
earlier adversarial review, and the index still called the set the source of
truth.

The filesystem registry, sidecar regeneration, and the pd-{language}-{typeface}-{task}-{date} names shipped. Legacy names stay read-only. Registry publish raises.

The original body was removed in the same change. Recover it from the
parent of the commit that set this file to superseded:
`git log -p -- specs/08-models.md`.

## What moved

Shipped behavior is in `docs/architecture/profiles-datasets-and-models.md`. Open, deferred, and dropped items are on
[the roadmap](../docs/roadmap.md).
