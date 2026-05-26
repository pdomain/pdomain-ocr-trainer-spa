# 19 — Deferred milestone: glyph-feature classifier

> **Status: ⏸ Deferred — post-core-parity (Phase 3).**
> Nothing in this spec is part of the core-parity milestone set
> (M0–M9). It is carried forward from the legacy `pd-ocr-trainer`
> roadmap (`docs/plans/roadmap.md` §Glyph-annotation milestones) so
> the design survives that repo's archival, and is **blocked on
> core-parity completion** plus upstream readiness (see §4).
>
> SPA milestones realizing this spec: **M13** (glyph eval slicing)
> and **M14** (glyph classifier) in
> [`16-milestones.md`](16-milestones.md). Design already woven into
> the core specs: [`06-training-runs.md`](06-training-runs.md) §5.4
> (glyph training run), [`07-evaluation-and-metrics.md`](07-evaluation-and-metrics.md)
> §4 (eval slicing). This file is the roadmap-level record.

---

## 1. Concept and feature taxonomy

Each OCR word may carry an optional `glyph_annotations` sidecar —
ct/st ligatures, long-s positions, swash caps, and similar
typographic features. Ground-truth text stays canonical; the
annotations live in parallel. The data model is owned by
`pdomain-book-tools`; training data is produced by `pdomain-ocr-synth` (gold)
and `pd-ocr-labeler` (human).

The feature set is one binary feature per `LigatureMark.kind`, plus
`long_s` and `swash`. `glyph_annotations is None` words are
**excluded** from both sliced metrics and classifier ground truth —
never silently counted as feature-absent. (Consistent with the
workspace rule that drop-cap / unannotated words are a weight signal
or an exclusion, never silent noise.)

The trainer has **two distinct, independently shippable** glyph
jobs — (g1) and (g2).

---

## 2. Milestone (g1) — glyph-annotation eval slicing  → SPA **M13**

*Cheap; ships first. A read-only consumer of `glyph_annotations` —
no new model.*

- The eval pipeline reports recognition CER/WER **sliced per glyph
  feature** (one bucket per `LigatureMark.kind`, plus `long_s`,
  `swash`).
- Words with `glyph_annotations is None` are excluded from sliced
  metrics.
- Output: a per-feature breakdown table in the run UI plus a JSON
  sidecar consumable by CI for regression alerts.
- **Ship criterion:** running eval against an annotated
  `<ml_validation_dir>/<profile>/recognition/` set produces overall
  CER/WER plus a per-feature table; features with N(pos) < 30 are
  flagged "low support."
- **Not blocked by (g2).**

SPA realization: eval-slicing logic + `EvalMetricsTable` slice
rendering — [`07-evaluation-and-metrics.md`](07-evaluation-and-metrics.md)
§4, [`16-milestones.md`](16-milestones.md) M13.

---

## 3. Milestone (g2) — glyph-feature classifier  → SPA **M14**

*A new model; ships after (g1).*

- A new training task in `pdomain-ocr-training` (a `train_glyph`
  entry point alongside detection / recognition), behind the same
  `ITrainingRunner` Protocol (D-T1).
- Model: a small CNN with a **multi-head sigmoid** output — one head
  per binary feature. Shared trunk + per-feature heads
  ([Q10](../OPEN_QUESTIONS.md)); architecture finalized by
  experiment.
- Training data: `pdomain-ocr-synth` (primary, weight ~0.8) +
  human-labeled crops from `pd-ocr-labeler` (secondary, weight ~0.2,
  upsampled).
- New HF dataset shape `pd-ocr-shape: glyph-classification/v1`; repo
  naming `<owner>/pd-ocr-<source>-<lang>-glyph`.
- Export: the standard model sidecar with `task:
  "glyph-classification"` plus per-feature `t_auto` / `t_suggest`
  thresholds, calibrated on a held-out **human-labeled** set:
  precision ≥ 0.99 for auto-fill, recall ≥ 0.9 for suggest.
- Eval is gated on the human-labeled held-out set, never synth.
- Inference consumer: the labeler pre-fills annotation suggestions
  that humans accept/reject — closing the loop.
- **Ship criterion:** the classifier exports against a synth + small
  human dataset, and the labeler loads the sidecar and pre-fills
  annotations on a sample page.

SPA realization: glyph kanban variant + run form + per-feature
metrics — [`04-profiles-and-config.md`](04-profiles-and-config.md)
§3.2, [`05-dataset-kanban.md`](05-dataset-kanban.md) §10,
[`06-training-runs.md`](06-training-runs.md) §5.4,
[`16-milestones.md`](16-milestones.md) M14.

---

## 4. Dependencies (why this is blocked)

Beyond core-parity completion, (g1)/(g2) are gated on upstream
readiness:

- **`pdomain-book-tools` `GlyphAnnotations` data model** must have
  landed, and at least one eval dataset must be annotated — gates
  (g1).
- **`pdomain-ocr-synth`** must emit `glyph-classification/v1` datasets —
  gates (g2).
- **`pd-ocr-labeler`** human glyph-annotation pipeline must exist —
  feeds (g2) training data and consumes the (g2) model.
- **`pdomain-ocr-training`** must grow the `train_glyph` recognition-peer
  task behind `ITrainingRunner` — gates (g2).

The SPA waits on all of these; it does not build ahead of them.

---

## 5. Citations

- Legacy roadmap, glyph milestones (g1)/(g2) + taxonomy preamble:
  `pd-ocr-trainer/docs/plans/roadmap.md:157-210`.
- Referenced legacy design specs (in the repo being archived):
  `pd-ocr-trainer/docs/specs/glyph-annotation-eval-slicing.md`,
  `pd-ocr-trainer/docs/specs/glyph-feature-classifier.md`.
- SPA adaptation: [`06-training-runs.md`](06-training-runs.md) §5.4,
  [`07-evaluation-and-metrics.md`](07-evaluation-and-metrics.md) §4,
  [`16-milestones.md`](16-milestones.md) M13–M14.
