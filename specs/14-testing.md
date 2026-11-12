---
Status: superseded
Owner: CT
Created: 2026-05-21
Last verified: 2026-11-12
Kind: spec
Promotes to: DEVELOPMENT.md
Disposition: Superseded by architecture and the roadmap. Original body is in git history.
---

# 14 — Testing strategy

## Agent Index

- **Kind:** spec
- **Status:** superseded
- **Read when:** an old link still names this file.
- **Search terms:** superseded, 14-testing.md

This file is not current truth. Read [DEVELOPMENT.md](../DEVELOPMENT.md).

## Adversarial Review

Reviewed against the code on 2026-11-12. This spec had no metadata and no
earlier adversarial review, and the index still called the set the source of
truth.

The unit, integration, slow, and e2e trees exist. The spec's denial of FakeTrainingRunner is wrong. MSW, transcript fixtures, the named Playwright scenario list, and nightly CI are not in the repo and are not backlog.

The original body was removed in the same change. Recover it from the
parent of the commit that set this file to superseded:
`git log -p -- specs/14-testing.md`.

## What moved

Shipped behavior is in `DEVELOPMENT.md`. Open, deferred, and dropped items are on
[the roadmap](../docs/roadmap.md).
