---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-13
Kind: issue
Level: I1
---

# M12 Typeface classifier

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-11-13
- **Resolution:** Open
- **Severity:** High — production typeface train/eval not real end-to-end
- **Affected version:** pdomain-ocr-trainer-spa master @ cutover 2026-07-21
- **Read when:** working on former GH #14, M12, typeface kanban, or upstream
  TypefaceConfig
- **Search terms:** former GH #14, M12, typeface classifier, TypefaceConfig,
  train_typeface, typeface-classification
- **Relates to:** [roadmap](../roadmap.md),
  [M12 plan](../plans/2026-06-10-m12-typeface-classifier.md),
  [umbrella #1](2026-07-21-gh-001-milestone-roadmap.md)

## Summary

M12 wires typeface-classifier training from `pdomain-ocr-training`, adds the
typeface kanban view and run form, and extends eval metrics per class.

The SPA has kanban and run-creation seams, classification result schema,
aggregate accuracy/F1 rendering, generic slice rows, and driver-contract tests.
It does not render `overall.per_class` as a class table or prove production
classification. The remaining classifier contract requires an owner scope
decision before implementation in an upstream package. Production builds
`LocalTrainingRunner` and calls `train_typeface` through a cast; the local
`TypefaceConfig` and a fake runner prove only the test seam. Classifier-package
scope remains an owner decision on the roadmap, not authorization to add those
methods to the existing training package.

Provenance: former GH #14. Tracks former GH #1. Still open on the
[remaining-work list](../roadmap.md).

## Impact

- Operators cannot complete a real typeface-classification/v1
  ingest → train → eval → publish round-trip against production runners.
- SPA tests prove the seam, not production training quality.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-trainer-spa
upstream: pdomain-ocr-training (TypefaceConfig + runners missing)
plan: docs/plans/2026-06-10-m12-typeface-classifier.md
dataset family: typeface-classification/v1
blocked_by_at_file: former GH #13 (now closed / shipped)
```

## Evidence

### 1. Original acceptance

- Round-trip: ingest a typeface-classification/v1 dataset, train, eval, publish
- Required verification: `just ci` must pass, plus a real round-trip for
  typeface-classification/v1. That production round-trip remains unverified.

### 2. SPA-side progress (former GH comment, 2026-06-10)

Comment on former GH #14: SPA M12 landed on local main (feat branch ending
`77c270a`): typeface-classification kanban (`metadata.jsonl`), run creation,
eval with per-class metrics, TypefaceKanbanPage + driver-contract testids,
nine Playwright e2e green. Left open for the upstream gate.

### 3. Intent map and current state

[Intent map](../context/intent-map.md) and
[current state](../context/current-state.md) still mark production typeface
train/eval as incomplete and blocked on upstream contracts.

## Root-cause hypotheses

1. **(Most likely) Missing classifier contract** — the local config and cast
   do not supply a production classifier. Upstream package scope awaits the owner.
2. **Stub masking gaps** — FakeTrainingRunner may hide contract mismatches until
   a real runner is wired.

## Defects to fix

1. **Confirm classifier-package scope with the owner** before scheduling an
   upstream implementation. Do not add methods to `pdomain-ocr-training`
   merely because the historical plan names that package.
2. **Integrate an approved classifier contract** in place of the local config
   and cast seam, keeping acceptance tests and fixing the metadata apply path.
3. **Prove the production round-trip**, including result rendering and publish,
   for typeface-classification/v1.

## Next steps

1. Confirm scope against the [roadmap](../roadmap.md). The
   [M12 plan](../plans/2026-06-10-m12-typeface-classifier.md) preserves an
   earlier cross-repo proposal, not implementation authorization.
2. Integrate real classifier dispatch only after its contract and package
   ownership are approved.
3. Run full ingest → train → eval → publish verification; then retire this
   issue.

## What is NOT broken (to scope the fix)

- SPA typeface kanban UI and API seams already present.
- Recognition/detection training paths unrelated to typeface.
- Former HF publish blocker (#13) is closed.

## Resolution

_Open._ When this issue is fixed, route it through `doc-retirer` with the resolving
commit and evidence. Promote durable behavior, update inbound references,
remove the live README pointer, and append a tombstone to the decision log.
Resolved reports are deleted; there is no resolved index to maintain.
