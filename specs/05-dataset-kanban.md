---
Status: superseded
Owner: CT
Created: 2026-05-21
Last verified: 2026-11-12
Kind: spec
Promotes to: docs/architecture/profiles-datasets-and-models.md
Disposition: Superseded by architecture and the roadmap. Original body is in git history.
---

# 05 — Dataset kanban

## Agent Index

- **Kind:** spec
- **Status:** superseded
- **Read when:** an old link still names this file.
- **Search terms:** superseded, 05-dataset-kanban.md

This file is not current truth. Read [docs/architecture/profiles-datasets-and-models.md](../docs/architecture/profiles-datasets-and-models.md).

## Adversarial Review

Reviewed against the code on 2026-11-12. This spec had no metadata and no
earlier adversarial review, and the index still called the set the source of
truth.

Detection, recognition, and typeface boards ship, with client staging and server apply. Typeface and glyph reads use metadata.jsonl. Apply writes labels.json for every task. Glyph classification returns dataset.task_unsupported, HTTP 501.

The original body was removed in the same change. Recover it from the
parent of the commit that set this file to superseded:
`git log -p -- specs/05-dataset-kanban.md`.

## What moved

Shipped behavior is in `docs/architecture/profiles-datasets-and-models.md`. Open, deferred, and dropped items are on
[the roadmap](../docs/roadmap.md).
