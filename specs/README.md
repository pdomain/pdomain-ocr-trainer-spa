# `pdomain-ocr-trainer-spa` Specs

Numbered design documents. Read [`00-overview.md`](00-overview.md)
first; it lists every other spec and tells you which to read for any
given implementation task.

> Specs are the **source of truth.** Code that disagrees with a spec is
> wrong; if reality forces a change, change the spec first, then the
> code.

| #  | File | Topic |
|----|------|-------|
| 00 | [`00-overview.md`](00-overview.md) | Goals, non-goals, tech stack, milestone contract |
| 01 | [`01-data-models.md`](01-data-models.md) | Pydantic + on-disk schemas (Profile, Dataset, Run, Model, Sidecar) |
| 02 | [`02-backend.md`](02-backend.md) | FastAPI router map, every endpoint contract, adapter Protocols |
| 03 | [`03-frontend.md`](03-frontend.md) | React shell, routing, state stores, generated client |
| 04 | [`04-profiles-and-config.md`](04-profiles-and-config.md) | Profile (group) management, OCR config, vocab, language/typeface |
| 05 | [`05-dataset-kanban.md`](05-dataset-kanban.md) | Unassigned / Training / Validation kanban; DnD; multi-select |
| 06 | [`06-training-runs.md`](06-training-runs.md) | Detection / Recognition / Typeface / Glyph training, params, logs |
| 07 | [`07-evaluation-and-metrics.md`](07-evaluation-and-metrics.md) | Eval, CER/WER, glyph-feature slicing |
| 08 | [`08-models.md`](08-models.md) | Model registry, sidecar, naming, on-disk + HF publishing |
| 09 | [`09-hf-integration.md`](09-hf-integration.md) | DatasetSource adapter, HF read/publish, auth, caching |
| 10 | [`10-jobs-and-sse.md`](10-jobs-and-sse.md) | Consuming the pdomain-ocr-ops LongJobRunner; SSE event shapes; cancellation |
| 11 | [`11-notifications.md`](11-notifications.md) | Toast queue, busy overlays, error surfacing |
| 12 | [`12-hotkeys-a11y.md`](12-hotkeys-a11y.md) | Keybindings, focus management, kanban a11y |
| 13 | [`13-driver-contract.md`](13-driver-contract.md) | data-testid + URL invariants for any future Playwright driver |
| 14 | [`14-testing.md`](14-testing.md) | pytest + Vitest + Playwright strategy; testing without GPU |
| 15 | [`15-deployment-dev.md`](15-deployment-dev.md) | Build, devcontainer, install, GPU/MPS |
| 16 | [`16-milestones.md`](16-milestones.md) | M0…M14 milestone breakdown |
| 17 | [`17-decisions.md`](17-decisions.md) | ADRs / decisions log |
| 18 | [`18-deferred-hf-datasets.md`](18-deferred-hf-datasets.md) | ⏸ Deferred — HF-datasets roadmap (post-core-parity) |
| 19 | [`19-deferred-glyph-classifier.md`](19-deferred-glyph-classifier.md) | ⏸ Deferred — glyph eval slicing + feature classifier (post-core-parity) |

## Conventions

- **Citations.** Whenever a spec asserts behaviour drawn from the
  legacy trainer, the labeler-spa, or pgdp-prep, the citation appears
  as `path:line`
  (e.g. `pdomain-ocr-training/src/pdomain_ocr_training/ui.py:247`).
- **Endpoints.** Always prefixed `/api/...`. Job endpoints use
  `/api/jobs/{job_id}/events` SSE, mirroring the labeler-spa.
- **Type names.** Wire models share a name with the domain Pydantic
  model unless the wire shape differs (then `<Verb><Noun>Request` /
  `<Verb><Noun>Response`).
- **`data-testid`.** Every interactive element keeps a stable testid;
  see [`13-driver-contract.md`](13-driver-contract.md).
- **Unresolved intent.** Link deferred or blocked choices to the
  [intent map](../docs/context/intent-map.md). Link shipped choices to current
  architecture or the [decisions record](../docs/context/decisions.md).
- **Re-use over re-spec.** When a topic is identical to the labeler
  SPA, link rather than duplicate (`see pdomain-ocr-labeler-spa
  specs/10-jobs-and-sse.md`).
