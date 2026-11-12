---
Status: superseded
Owner: CT
Created: 2026-05-21
Last verified: 2026-11-12
Kind: spec
Promotes to: docs/architecture/shell-and-jobs.md
Disposition: Superseded by architecture and the roadmap. Original body is in git history.
---

# 11 — Notifications

## Agent Index

- **Kind:** spec
- **Status:** superseded
- **Read when:** an old link still names this file.
- **Search terms:** superseded, 11-notifications.md

This file is not current truth. Read [docs/architecture/shell-and-jobs.md](../docs/architecture/shell-and-jobs.md).

## Adversarial Review

Reviewed against the code on 2026-11-12. This spec had no metadata and no
earlier adversarial review, and the index still called the set the source of
truth.

Banners and the sonner mount shipped. useNotificationStream is not mounted. There is no BusyOverlay and no /settings route for the token banner.

The original body was removed in the same change. Recover it from the
parent of the commit that set this file to superseded:
`git log -p -- specs/11-notifications.md`.

## What moved

Shipped behavior is in `docs/architecture/shell-and-jobs.md`. Open, deferred, and dropped items are on
[the roadmap](../docs/roadmap.md).
