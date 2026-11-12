---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-06
Kind: issue
Level: I1
---

# M13 Glyph eval slicing

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-11-06
- **Resolution:** Open
- **Severity:** Medium — glyph eval metrics lack annotation-keyed slices
- **Affected version:** pdomain-ocr-trainer-spa master @ cutover 2026-07-21
- **Read when:** working on former GH #15, M13, GlyphAnnotations, or eval
  metrics table slices
- **Search terms:** former GH #15, M13, glyph eval, GlyphAnnotations, metrics
  slicing
- **Relates to:** [roadmap](../roadmap.md),
  [runs and evaluation](../architecture/runs-and-evaluation.md),
  [umbrella #1](2026-07-21-gh-001-milestone-roadmap.md)

## Summary

M13 extends the evaluation pipeline with slicing keyed on `GlyphAnnotations`
and adds per-feature rows to the eval metrics table.

The open acceptance is on the [roadmap](../roadmap.md): a recognition eval
with slicing writes `slices[]` for every labelled feature, the table sorts by
absolute CER delta, and rows with fewer than 30 positive samples are low
support. M14 depends on this work. The old spec body is git history.

Provenance: former GH #15. Tracks former GH #1. Still open on the
[remaining-work list](../roadmap.md).

## Impact

- Glyph-related eval cannot present feature-level slices operators need.
- M14 glyph classifier work is blocked on this milestone completing.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-trainer-spa
spec: docs/roadmap.md (glyph-slice acceptance)
depends_on: stable eval / HF path (former GH #13 closed)
blocks: former GH #16 / M14
```

## Evidence

### 1. Original acceptance

- Acceptance now recorded on the roadmap (formerly specs/07 §8)
- Verification: `make ci` green; eval slicing acceptance tests pass

### 2. Roadmap placement

The [remaining-work list](../roadmap.md) still includes M13. On 2026-11-12,
`worker/evaluate.py` `_build_runner` still raises `RuntimeError` and never
calls `LocalEvalRunner`. The text inside that raise says glyph input is
missing and that recognition eval hard-codes `slices=[]`. That text is stale
against installed `pdomain-ocr-training` 0.2.1, which already has
`glyph_annotations_path` and `slice_glyph_features`.
`tests/unit/worker/test_evaluate.py`
`test_build_runner_surfaces_upstream_gap` locks the raise.

### 3. Spec authority

Shipped eval behavior is in
[runs and evaluation](../architecture/runs-and-evaluation.md). Implement the
gap against the roadmap acceptance and `worker/evaluate.py`, not the
superseded spec stub.

## Root-cause hypotheses

1. **(Most likely) Deferred post-core milestone** — intentionally after M11.
2. **Annotation contract not fully consumed** — UI/API may lack
   GlyphAnnotations wiring even if models carry fields.

## Defects to fix

1. **Slicing logic on GlyphAnnotations** in the eval pipeline.
2. **Per-feature rows** in the eval metrics table.
3. **Acceptance tests** for the roadmap glyph-slice acceptance.

## Next steps

1. Read the roadmap acceptance and map gaps in `worker/evaluate.py` and the eval UI.
2. Implement slicing + table rows with failing tests first.
3. Unblock [M14](2026-07-21-gh-016-m14-glyph-classifier.md) when green.

## What is NOT broken (to scope the fix)

- The eval form and result routes exist. The production runner still raises
  before any real score, including detection and recognition.
- Typeface per-class metrics (M12 SPA) are a separate slice dimension.
- Former #13 HF publish blocker is closed.

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
