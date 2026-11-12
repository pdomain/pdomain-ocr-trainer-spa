---
Status: superseded
Owner: CT
Created: 2026-05-21
Last verified: 2026-11-12
Kind: spec
Promotes to: docs/architecture/trainer-workflows.md
Disposition: Index of superseded design stubs. Not the source of truth.
---

# Specs

## Agent Index

- **Kind:** spec
- **Status:** superseded
- **Read when:** following an old link into `specs/`.
- **Search terms:** superseded specs, design stubs, driver contract

These files are not the source of truth. Shipped behavior is under
[docs/architecture/](../docs/architecture/trainer-workflows.md). Remaining work
is [docs/roadmap.md](../docs/roadmap.md).

## Adversarial Review

Reviewed against the code on 2026-11-12. The previous index said that code
which disagrees with a spec is wrong. That rule conflicts with the 2026-07-14
decision to record shipped behavior from the code. The numbered files except
`13-driver-contract.md` are stubs. Their old bodies are in git history.

## What remains in full

[13-driver-contract.md](13-driver-contract.md) stays. `tests/e2e/test_driver_contract.py`
parses its tables. Do not replace that file until the test reads the replacement.

New design specs, when a milestone is still open, belong in `docs/specs/` per
[CONVENTIONS.md](../CONVENTIONS.md).
