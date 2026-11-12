---
Status: superseded
Owner: CT
Created: 2026-05-21
Last verified: 2026-11-12
Kind: spec
Promotes to: docs/architecture/trainer-workflows.md
Disposition: Superseded by architecture and the roadmap. Original body is in git history.
---

# 02 — Backend

## Agent Index

- **Kind:** spec
- **Status:** superseded
- **Read when:** an old link still names this file.
- **Search terms:** superseded, 02-backend.md

This file is not current truth. Read [docs/architecture/trainer-workflows.md](../docs/architecture/trainer-workflows.md).

## Adversarial Review

Reviewed against the code on 2026-11-12. This spec had no metadata and no
earlier adversarial review, and the index still called the set the source of
truth.

The process boundary shipped. The route table both omitted shipped routes and specified routes that were never added. Those missing routes are dropped on the roadmap, not queued. Publish submission raises AdapterNotImplementedError.

The original body was removed in the same change. Recover it from the
parent of the commit that set this file to superseded:
`git log -p -- specs/02-backend.md`.

## What moved

Shipped behavior is in `docs/architecture/trainer-workflows.md`. Open, deferred, and dropped items are on
[the roadmap](../docs/roadmap.md).
