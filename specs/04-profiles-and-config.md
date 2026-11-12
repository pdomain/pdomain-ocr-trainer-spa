---
Status: superseded
Owner: CT
Created: 2026-05-21
Last verified: 2026-11-12
Kind: spec
Promotes to: docs/architecture/profiles-datasets-and-models.md
Disposition: Superseded by architecture and the roadmap. Original body is in git history.
---

# 04 — Profiles and config

## Agent Index

- **Kind:** spec
- **Status:** superseded
- **Read when:** an old link still names this file.
- **Search terms:** superseded, 04-profiles-and-config.md

This file is not current truth. Read [docs/architecture/profiles-datasets-and-models.md](../docs/architecture/profiles-datasets-and-models.md).

## Adversarial Review

Reviewed against the code on 2026-11-12. This spec had no metadata and no
earlier adversarial review, and the index still called the set the source of
truth.

Profile files, the all profile, and detection or recognition defaults shipped. Vocab scan, vocab list, batch suggestion, and a device list were never built and are dropped.

The original body was removed in the same change. Recover it from the
parent of the commit that set this file to superseded:
`git log -p -- specs/04-profiles-and-config.md`.

## What moved

Shipped behavior is in `docs/architecture/profiles-datasets-and-models.md`. Open, deferred, and dropped items are on
[the roadmap](../docs/roadmap.md).
