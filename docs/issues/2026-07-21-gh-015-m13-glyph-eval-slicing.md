---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: issue
Level: I1
---

# M13 Glyph eval slicing

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-21
- **Resolution:** Open
- **Severity:** Medium — glyph eval metrics lack annotation-keyed slices
- **Affected version:** pdomain-ocr-trainer-spa master @ cutover 2026-07-21
- **Read when:** working on former GH #15, M13, GlyphAnnotations, or eval
  metrics table slices
- **Search terms:** former GH #15, M13, glyph eval, GlyphAnnotations, metrics
  slicing
- **Relates to:** [roadmap](../roadmap.md),
  [specs/07-evaluation-and-metrics](../../specs/07-evaluation-and-metrics.md),
  [umbrella #1](2026-07-21-gh-001-milestone-roadmap.md)

## Summary

M13 extends the evaluation pipeline with slicing keyed on `GlyphAnnotations`
and adds per-feature rows to the eval metrics table.

Acceptance is defined in `specs/07-evaluation-and-metrics.md` §8. Former
blocker #13 (HF publish path) is closed. M14 depends on this work.

Provenance: former GH #15. Tracks former GH #1. Roadmap priority: **Next**.

## Impact

- Glyph-related eval cannot present feature-level slices operators need.
- M14 glyph classifier work is blocked on this milestone completing.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-trainer-spa
spec: specs/07-evaluation-and-metrics.md §8
depends_on: stable eval / HF path (former GH #13 closed)
blocks: former GH #16 / M14
```

## Evidence

### 1. Original acceptance

- Acceptance from `specs/07-evaluation-and-metrics.md` §8
- Verification: `make ci` green; eval slicing acceptance tests pass

### 2. Roadmap placement

Standing [roadmap](../roadmap.md) lists M13 under **Next**, after typeface
residual and jobs-surface residual.

### 3. Spec authority

Design for evaluation surfaces and metrics remains in
`specs/07-evaluation-and-metrics.md`; implement against that section, not the
retired multi-milestone plan file alone.

## Root-cause hypotheses

1. **(Most likely) Deferred post-core milestone** — intentionally after M11.
2. **Annotation contract not fully consumed** — UI/API may lack
   GlyphAnnotations wiring even if models carry fields.

## Defects to fix

1. **Slicing logic on GlyphAnnotations** in the eval pipeline.
2. **Per-feature rows** in the eval metrics table.
3. **Acceptance tests** for specs/07 §8.

## Next steps

1. Read specs/07 §8 and map gaps in current eval API + UI.
2. Implement slicing + table rows with failing tests first.
3. Unblock [M14](2026-07-21-gh-016-m14-glyph-classifier.md) when green.

## What is NOT broken (to scope the fix)

- Core recognition/detection eval paths already shipped in M7+.
- Typeface per-class metrics (M12 SPA) are a separate slice dimension.
- Former #13 HF publish blocker is closed.

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
