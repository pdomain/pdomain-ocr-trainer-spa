---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: issue
Level: I1
---

# M12 Typeface classifier

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-21
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

SPA-side work has shipped (kanban, run creation, per-class eval UI,
driver-contract testids, Playwright coverage). The remaining gate is upstream:
`TypefaceConfig`, `ITrainingRunner.train_typeface`, and
`IEvalRunner.evaluate_typeface` in `pdomain-ocr-training`. Until then the SPA
uses a local TypefaceConfig stub and FakeTrainingRunner.

Provenance: former GH #14. Tracks former GH #1. Roadmap priority: **Now**.

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
- Verification: `make ci` green; round-trip for typeface-classification/v1

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

1. **(Most likely) Cross-repo gate** — SPA finished its side; training package
   has not shipped the Protocol methods yet.
2. **Stub masking gaps** — FakeTrainingRunner may hide contract mismatches until
   a real runner is wired.

## Defects to fix

1. **Upstream TypefaceConfig + train/eval runners** in `pdomain-ocr-training`.
2. **SPA cutover off stub** — dispatch real runners; keep acceptance tests.
3. **Prove round-trip** for typeface-classification/v1 publish path.

## Next steps

1. Track or implement upstream Protocol per
   [M12 plan](../plans/2026-06-10-m12-typeface-classifier.md) §Cross-repo gate.
2. Replace stub dispatch when upstream is available.
3. Run full ingest → train → eval → publish verification; then retire this
   issue.

## What is NOT broken (to scope the fix)

- SPA typeface kanban UI and API seams already present.
- Recognition/detection training paths unrelated to typeface.
- Former HF publish blocker (#13) is closed.

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit/upstream refs here, move the README pointer to Resolved, and
route retirement through `doc-retirer`.
