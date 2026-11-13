---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-13
Kind: issue
Level: I1
---

# M14 Glyph classifier

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-11-13
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

M14 requires an approved glyph classifier contract, run and eval integration,
and a real publish round-trip against the ROADMAP (g2) ship criterion.
Production classifier support is not implemented; package scope remains an
owner decision.

Blocked by M13 (glyph eval slicing) and by unavailable typed classifier
training/config contracts. The intent map keeps classifier-package scope
blocked on the owner decision.

Provenance: former GH #16. Tracks former GH #1. Still open on the
[remaining-work list](../roadmap.md). On 2026-11-06,
`test_glyph_classifier_task_still_rejected` still expects HTTP 501
`dataset.task_unsupported`.

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
- Required verification: `just ci` must pass, plus a full production
  glyph-classifier round-trip. That round-trip remains unverified.

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

1. **Obtain an approved classifier contract and package choice**, then wire
   glyph training. Do not infer that new methods belong in the existing
   `pdomain-ocr-training` package.
2. **Extend run form and eval pages** for glyph-classifier jobs.
3. **Publish round-trip** meeting ROADMAP (g2).

## Next steps

1. Finish [M13](2026-07-21-gh-015-m13-glyph-eval-slicing.md).
2. Confirm the owner's package scope and the required glyph contracts before
   scheduling upstream implementation.
3. Implement SPA wiring + acceptance; then retire this issue.

## What is NOT broken (to scope the fix)

- Detection and recognition training call `LocalTrainingRunner`.
- M12 typeface SPA seam (separate task family). Production typeface training
  is still the cast described on the roadmap.
- The old `specs/19` body is a superseded stub. This issue and the roadmap are
  the glyph-classifier record.

## Resolution

_Open._ When this issue is fixed, route it through `doc-retirer` with the resolving
commit and evidence. Promote durable behavior, update inbound references,
remove the live README pointer, and append a tombstone to the decision log.
Resolved reports are deleted; there is no resolved index to maintain.
