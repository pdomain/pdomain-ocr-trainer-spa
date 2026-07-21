---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: issue
Level: I1
---

# M14 Glyph classifier

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-21
- **Resolution:** Open
- **Severity:** High — glyph-classifier training not end-to-end
- **Affected version:** pdomain-ocr-trainer-spa master @ cutover 2026-07-21
- **Read when:** working on former GH #16, M14, glyph classifier training, or
  ROADMAP (g2)
- **Search terms:** former GH #16, M14, glyph classifier, train glyph,
  ROADMAP g2
- **Relates to:** [roadmap](../roadmap.md),
  [M13](2026-07-21-gh-015-m13-glyph-eval-slicing.md),
  [umbrella #1](2026-07-21-gh-001-milestone-roadmap.md),
  [intent map](../context/intent-map.md)

## Summary

M14 wires the glyph classifier training task from `pdomain-ocr-training`,
extends run form and eval pages for glyph-classifier jobs, and completes a
publish round-trip against the ROADMAP (g2) ship criterion.

Blocked by M13 (glyph eval slicing) and by upstream typed classifier training /
config contracts in `pdomain-ocr-training` (intent map **Blocked**).

Provenance: former GH #16. Tracks former GH #1. Roadmap priority: **Later**.

## Impact

- Glyph-classifier workflows cannot train or publish end-to-end from the SPA.
- Post-core roadmap (g2) ship criterion remains unmet.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-trainer-spa
upstream: pdomain-ocr-training (glyph classifier train/config contracts)
blocked_by: former GH #15 / M13; upstream contracts
ship_criterion: ROADMAP (g2)
```

## Evidence

### 1. Original acceptance

- Round-trip per the ROADMAP (g2) ship criterion
- Verification: `make ci` green; full glyph-classifier round-trip

### 2. Intent map Blocked

[Intent map](../context/intent-map.md) states glyph-classifier training is
blocked on typed classifier training and configuration contracts in
`pdomain-ocr-training`.

### 3. Dependency chain

Former GH body: blocked by #15. M13 issue file is the in-repo successor of that
dependency.

## Root-cause hypotheses

1. **(Most likely) Double dependency** — needs M13 SPA eval work and upstream
   training contracts before a real round-trip is possible.
2. **Ship criterion broader than SPA** — g2 may include packaging and publish
   steps outside this repo alone.

## Defects to fix

1. **Wire glyph-classifier training task** from `pdomain-ocr-training`.
2. **Extend run form and eval pages** for glyph-classifier jobs.
3. **Publish round-trip** meeting ROADMAP (g2).

## Next steps

1. Finish [M13](2026-07-21-gh-015-m13-glyph-eval-slicing.md).
2. Confirm upstream glyph training/config Protocols exist or file them.
3. Implement SPA wiring + acceptance; then retire this issue.

## What is NOT broken (to scope the fix)

- Core recognition/detection train/eval/publish paths.
- M12 typeface SPA seam (separate task family).
- Spec deferred notes in `specs/19-deferred-glyph-classifier.md` remain design
  context, not proof of implementation.

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit/upstream refs here, move the README pointer to Resolved, and
route retirement through `doc-retirer`.
