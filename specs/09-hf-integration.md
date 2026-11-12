---
Status: superseded
Owner: CT
Created: 2026-05-21
Last verified: 2026-11-12
Kind: spec
Promotes to: docs/architecture/huggingface.md
Disposition: Superseded by architecture and the roadmap. Original body is in git history.
---

# 09 — Hugging Face integration

## Agent Index

- **Kind:** spec
- **Status:** superseded
- **Read when:** an old link still names this file.
- **Search terms:** superseded, 09-hf-integration.md

This file is not current truth. Read [docs/architecture/huggingface.md](../docs/architecture/huggingface.md).

## Adversarial Review

Reviewed against the code on 2026-11-12. This spec had no metadata and no
earlier adversarial review, and the index still called the set the source of
truth.

Dataset preview shipped. Publish routes validate, then the worker helper raises. enable_hf_publish does not gate the routes. S3 and the Hub model registry raise on use.

The original body was removed in the same change. Recover it from the
parent of the commit that set this file to superseded:
`git log -p -- specs/09-hf-integration.md`.

## What moved

Shipped behavior is in `docs/architecture/huggingface.md`. Open, deferred, and dropped items are on
[the roadmap](../docs/roadmap.md).
