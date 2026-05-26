# 07 — Evaluation and metrics

How a trained model is evaluated against a labelled validation set,
how the SPA renders results, and how glyph-feature slicing
(milestone (g1) in the trainer ROADMAP) surfaces.

> Required reading: [`01-data-models.md`](01-data-models.md) §3,
> [`06-training-runs.md`](06-training-runs.md) (eval shares the run
> machinery), `pd-ocr-trainer/docs/specs/glyph-annotation-eval-slicing.md`
> (the underlying spec; this doc adapts it to the SPA surface).

---

## 1. Eval is a run

An eval is a `Run` with `kind="eval"`. Same on-disk layout, same
SSE event stream, same `runs/<id>/` structure. Two distinguishing
fields:

- `Run.task` is the task being evaluated (`detection | recognition |
  typeface-classification | glyph-classification`).
- `Run.args` carries `model_name`, `val_source` (defaults to
  `local: ml-validation/<profile>/<task>/`), and any task-specific
  flags (e.g. `slice_glyph_features: true`).

Artefacts emitted by an eval run:

- `runs/<id>/result.json` — the typed `EvalResult` (see §3).
- `runs/<id>/result.md` — pretty-printed markdown for UI reuse / CI
  archival.
- For recognition: optionally `runs/<id>/predictions.jsonl` —
  `{file_name, gt, pred, cer, wer}` per crop, gated by
  `args.persist_predictions: bool` (default false; large data).

---

## 2. Endpoints

```
POST /api/eval
     body: EvalRequest
     → 202 { run_id, job_id }

GET  /api/eval/{run_id}/result
     → EvalResult                                          (200)
     # 404 if not yet finished, 409 if run is failed/cancelled

GET  /api/eval/compare
     query: ?run_ids=a,b,c
     → EvalComparison                                      (200)
     # joins matching feature buckets across runs (latest-first column order)

GET  /api/runs/{run_id}/predictions
     query: ?cer_min=0.0&cer_max=1.0&page=0&size=50
     → PredictionsPage                                     (200)
     # only if args.persist_predictions == true; else 404
```

`EvalRequest`:

```python
class EvalRequest(BaseModel):
    profile: str
    task: TaskEnum
    model_name: str                               # required
    val_source: DatasetSourceRef | None = None    # default: local profile val dir
    persist_predictions: bool = False
    slice_glyph_features: bool = False            # (g1); recognition only
    notes: str | None = None
```

---

## 3. `EvalResult`

```python
class EvalResult(BaseModel):
    run_id: str
    profile: str
    task: TaskEnum
    model_name: str
    val_source: DatasetSourceRef
    overall: EvalMetrics
    slices: list[EvalSlice] = []                  # populated by slice_glyph_features and/or per-class
    sample_count: int                             # words for recognition / glyph; pages for detection; crops for typeface
    excluded_count: int = 0                       # for slicing — words/crops with annotation == None
    duration_seconds: float
    finished_at: datetime

class EvalMetrics(BaseModel):
    """Task-shaped. Only the fields relevant to `task` are populated; others are None."""
    # Recognition
    cer: float | None = None                      # in [0, 1]
    wer: float | None = None
    exact_match_rate: float | None = None
    # Detection
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    iou_50: float | None = None
    iou_50_95: float | None = None                # COCO-style mAP avg
    # Classification (typeface, per-feature glyph)
    accuracy: float | None = None
    f1_macro: float | None = None
    per_class: dict[str, ClassMetrics] | None = None

class ClassMetrics(BaseModel):
    n: int
    precision: float
    recall: float
    f1: float

class EvalSlice(BaseModel):
    feature: str                                  # e.g. "ligature:CT", "long_s", "swash", or "class:roman"
    n_pos: int
    n_neg: int
    n_excluded: int
    cer_pos: float | None = None                  # recognition slicing
    cer_neg: float | None = None
    wer_pos: float | None = None
    wer_neg: float | None = None
    delta_cer: float | None = None                # cer_pos - cer_neg; signed
    low_support: bool                             # n_pos < 30
```

---

## 4. Glyph-feature slicing (g1)

Recognition eval only. Activated by
`EvalRequest.slice_glyph_features: true`.

Slicing rules (verbatim from
`pd-ocr-trainer/docs/specs/glyph-annotation-eval-slicing.md`):

- For each binary feature `f` in
  `{ligature:<kind>, long_s, swash}`:
  - `positive` = words where `glyph_annotations is not None` AND
    `f` is present.
  - `negative` = words where `glyph_annotations is not None` AND
    `f` is absent.
  - `excluded` = words where `glyph_annotations is None`.
- CER + WER computed per (positive, negative) set. Excluded words
  are **never** in the denominator.
- Ligatures slice **per `kind`** — never a single lumped
  "ligatures-present" bucket.
- `low_support = (n_pos < 30)` — display the row, but the SPA shows
  it greyed and tagged "low support".

The frontend `EvalMetricsTable` renders the slices below the
overall metrics, sorted by `|delta_cer|` descending. CSV export
("Download metrics") emits a flat table with one row per slice.

---

## 5. Per-class slicing (typeface, glyph classifier)

For typeface and glyph classifier eval, `slices` carries a
`feature: "class:<value>"` row per class with `n_pos`, `n_neg`,
`precision`, `recall`, `f1`. The `EvalSlice` shape is reused;
recognition fields stay `None`.

---

## 6. UI

### 6.1 Eval form (`/eval`)

- Profile selector → defaults to active profile.
- Task radio (detection / recognition / typeface-classification /
  glyph-classification).
- Model dropdown — populated from `GET /api/models?profile=&task=`.
  Filtered to matching `(profile, task)` by default; "Show all" toggle.
- Validation source — radio:
  - "Local" (default): uses `ml-validation/<profile>/<task>/`.
  - "Custom path": filepicker. Validates existence on submit.
  - "Hugging Face dataset": dataset repo + revision; gated by
    `Settings.enable_hf_publish` flag (HF read path is enabled on
    the same flag for v1; can split later — [Q15](../OPEN_QUESTIONS.md)).
- Checkboxes:
  - `[ ] Slice by glyph annotations` (recognition only).
  - `[ ] Persist per-prediction details` (recognition only).
- `[Run eval]` → `POST /api/eval` → bounce to `/runs/{run_id}`.

### 6.2 Eval result page (`/eval/{run_id}/result`)

```
┌──────────────────────────────────────────────────────────────┐
│  Profile · Task · Model                                       │
│  Overall: CER 0.034   WER 0.092   N 18675                     │
├──────────────────────────────────────────────────────────────┤
│  EvalMetricsTable                                             │
│  Feature        | N pos | N neg | CER pos | CER neg | Δ CER  │
│  long_s         |   412 | 18163 |   0.142 |   0.033 | +0.109 │
│  ligature:CT    |   142 | 18433 |   0.081 |   0.034 | +0.047 │
│  ligature:ST    |    88 | 18487 |   0.063 |   0.034 | +0.029 │
│  swash (low)    |    27 | 18548 |   0.052 |   0.034 | +0.018 │  // grey row
├──────────────────────────────────────────────────────────────┤
│  Predictions browser  (only if persist_predictions)           │
│  [search by GT/pred] [filter cer >= 0.0] [paginated table]    │
└──────────────────────────────────────────────────────────────┘
```

Action buttons:
- `[Download JSON]` → result.json.
- `[Download Markdown]` → result.md.
- `[Compare with…]` → `EvalCompareDialog` (multi-pick from
  recent eval runs of same task).

### 6.3 Compare view (`?compare=run_id1,run_id2,...`)

Side-by-side `EvalMetricsTable` per run, joined by feature key.
Sorting: `delta_cer` of leftmost run, descending. Differences > 1pp
are highlighted (red if worse than leftmost, green if better).

---

## 7. CI integration

A regression-alert script (not part of the SPA itself) consumes
`runs/<id>/result.json` and posts to a configurable webhook when:

- Overall metric regresses by > 0.5 pp vs the latest tagged baseline.
- Any per-feature `cer_pos` regresses by > 1 pp on a slice with
  `n_pos >= 30`.

Spec for the webhook lives outside this repo
([Q16](../OPEN_QUESTIONS.md)).

---

## 8. Acceptance behaviour

1. Train a recognition model on `clogaelach`. From its model page,
   click "Open Eval". The eval form prefills profile, task,
   model_name; defaults to the local val dir.
2. Toggle "Slice by glyph annotations". Submit. The eval run runs
   to completion; result.json contains `slices[]` populated for
   every feature with at least one labelled occurrence.
3. The metrics table sorts by `|delta_cer|` desc and greys rows
   with `n_pos < 30`.
4. Re-train, eval again. Compare view shows side-by-side; the row
   for `long_s` shows a green "−0.04" delta indicating
   improvement.

---

## 9. Citations

- Eval-slicing motivation + math: `pd-ocr-trainer/docs/specs/glyph-annotation-eval-slicing.md`.
- Glyph data model: `pdomain-book-tools` `GlyphAnnotations` (cross-repo).
- Detection eval shape: existing `train_detect.py` post-train eval
  pass.
- Recognition eval shape: existing `train_recog.py` post-train eval
  pass (CER/WER computation already there).
