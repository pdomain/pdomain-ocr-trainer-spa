---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: issue
Level: I1
---

# pd-ocr-trainer-spa milestone roadmap (M0–M14)

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-21
- **Resolution:** Open
- **Severity:** Medium — umbrella tracker for remaining post-core milestones
- **Affected version:** pdomain-ocr-trainer-spa master @ cutover 2026-07-21
- **Read when:** orienting to M0–M14 status or former GH #1
- **Search terms:** former GH #1, M0-M14, milestone roadmap, trainer SPA
- **Relates to:** [roadmap](../roadmap.md),
  [specs/16-milestones](../../specs/16-milestones.md)

## Summary

Umbrella tracking issue for the FastAPI + React/Vite/TS trainer SPA that
replaced the legacy NiceGUI `pd-ocr-trainer` UI. Design lives in `specs/00-19`.
Fifteen milestones (M0–M14): infrastructure M0–M3, core vertical slices M4–M9,
post-core roadmap M10–M14.

At cutover, M0–M11 are closed/shipped. Open legs are M12–M14 plus residual jobs
surface work. Prefer the standing [roadmap](../roadmap.md) and the per-milestone
issue files for day-to-day work; keep this file as the former #1 provenance
node.

Provenance: former GH #1.

## Impact

- Without a single umbrella record, agents re-open closed milestone scope.
- Remaining post-core work still needs a clear parent for M12–M14 reports.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-trainer-spa
design: specs/00-19 (esp. specs/16-milestones.md)
standing backlog: docs/roadmap.md
retired plan path: docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md
  (retired 2026-07-14; see docs/context/decisions.md)
```

## Evidence

### 1. Shipped core milestones

Roadmap shipped ledger lists former GH #2–#13 (M0–M11) as closed. Architecture
is recorded in [trainer workflows](../architecture/trainer-workflows.md).

### 2. Open children

- [M12 Typeface classifier](2026-07-21-gh-014-m12-typeface-classifier.md)
- [M13 Glyph eval slicing](2026-07-21-gh-015-m13-glyph-eval-slicing.md)
- [M14 Glyph classifier](2026-07-21-gh-016-m14-glyph-classifier.md)

### 3. Original body

Tracking spec for the pd-ocr-trainer-spa implementation roadmap. Plan path
cited `docs/plans/2026-05-21-pd-ocr-trainer-spa-milestones.md` (later retired
into architecture + intent map).

## Root-cause hypotheses

1. **(Most likely) Planned multi-milestone program** — not a single defect; open
   residual is intentional post-core work.
2. **Plan doc retirement** — umbrella still useful as provenance after the
   milestone plan file was retired.

## Defects to fix

1. **Drive remaining open children to resolution** — M12 upstream gate, M13
   eval slicing, M14 glyph classifier.
2. **Retire this umbrella** when M12–M14 are done (or explicitly deferred) via
   `doc-retirer`.

## Next steps

1. Work open children from [roadmap](../roadmap.md) Now / Next / Later.
2. Do not recreate the retired multi-milestone plan file unless owners ask.
3. When all children are resolved or deferred, retire this issue report.

## What is NOT broken (to scope the fix)

- Core M0–M11 product paths already shipped.
- Spec set `specs/00-19` remains the design authority.

## Resolution

_Open._ When M12–M14 are resolved or deferred: set `Status: retired`, link
child resolutions, move the README pointer to Resolved, route through
`doc-retirer`.
