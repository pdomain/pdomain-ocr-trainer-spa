# 18 — Deferred milestone: HF-datasets roadmap

> **Status: ⏸ Deferred — post-core-parity (Phase 3).**
> Nothing in this spec is part of the core-parity milestone set
> (M0–M9). It is carried forward from the legacy `pdomain-ocr-training`
> roadmap (`docs/plans/roadmap.md`) so the design survives that
> repo's archival, and is **blocked on core-parity completion** —
> the SPA must reach functional parity with the legacy NiceGUI
> trainer before any HF-datasets work begins.
>
> Governing decisions: **D-T2** (dataset sources — `local` in core,
> `huggingface` deferred) and **D-T11** (per-row licensing
> deferred) in [`17-decisions.md`](17-decisions.md).
>
> SPA milestones realizing this spec: **M10** (HF read path) and
> **M11** (HF publish path) in [`16-milestones.md`](16-milestones.md).
> Design detail already adapted to the SPA stack:
> [`09-hf-integration.md`](09-hf-integration.md).

This spec is the **roadmap-level** record. `09-hf-integration.md`
holds the concrete adapter/route design; this file holds the
milestone sequencing, ship criteria, and headline decisions carried
from the legacy roadmap.

---

## 1. Headline decisions (carried from the legacy roadmap)

- **HF dataset publishing lives in the trainer**, not the labeler.
  The labeler labels; the trainer consumes labeled data, so it owns
  packaging, publishing, and versioning. In the new stack that
  ownership lands in `pdomain-ocr-trainer-spa` (publish routes) backed by
  the `pdomain-ocr-training` / `pdomain-ocr-ops` libraries.
- **Two attributes are required on every dataset and every model:**
  - `language` — BCP-47 lowercase, open string (`en`, `ga`, `de`,
    `el`, `grc`, `la`, …).
  - `typeface` — closed enum.
- **`typeface` is a hard filter, not a tag.** Detection and
  recognition models train on a single typeface variant; there is
  no `mixed` typeface at publish time.
- **Per-row `license` (SPDX)** is required in the dataset schema;
  publish refuses when a row's source license is missing (D-T11 —
  deferred to this milestone, not core parity).

---

## 2. Milestones

Each is independently shippable, in order. SPA mapping in brackets.

### (a) HF read path alongside local  → SPA **M10**

- A `DatasetSource` seam with two impls: `local` (core-parity
  default) and `huggingface` (`datasets.load_dataset` + the DocTR
  adapter). In the SPA this is the `IDatasetSource` Protocol
  ([`02-backend.md`](02-backend.md) §4.4); the `huggingface` impl is
  `NotImplementedYet` until this milestone.
- A `Run` may carry an ordered `sources:` list; mixing is explicit
  (no silent fan-out).
- `HF_HOME` points at the shared AI cache volume.
- **Ship criterion:** a profile with a single `hf:` source trains
  end-to-end against a hand-uploaded test dataset.

### (a.5) Typeface-classifier read path  → SPA **M12**

- Reuses the `DatasetSource` seam from (a). The loader recognizes
  `pd-ocr-shape: typeface-classification/v1` and yields
  `(image, typeface)` pairs.
- A deliberately small image-classification model (architecture
  TBD; see the [blocked production round-trip](../docs/context/intent-map.md)).
- **Ship criterion:** a classifier profile with one `hf:` source
  trains end-to-end against a hand-uploaded test dataset.

### (b) Trainer publishes datasets  → SPA **M11**

- Publish routes (`POST /api/publish/dataset`) wrap
  `huggingface_hub.HfApi.upload_large_folder`.
- Emits imagefolder + `metadata.jsonl` for recognition, parquet for
  detection, imagefolder + `metadata.jsonl` (with a `typeface`
  column) for typeface-classification.
- Generates a `README.md` dataset card with YAML front matter
  (license, language, tags, `pd_ocr_*` keys).
- Idempotent: skips when the local snapshot hash matches the remote
  tip.
- **Ship criterion:** round-trip — publish, then load via (a) and
  train.

### (c) Backfill existing corpora  → post-M11 operational task

- One-off backfill of the existing on-disk corpora into HF repos.
- An interactive script prompts the operator for `(language,
  typeface)` per project.
- Prefer `matched-ocr/` as the source — it carries the richer
  pdomain-book-tools page document, not the derived `labels.json`.
- The labeler's per-word style flags are also backfilled into a
  typeface-classifier dataset in the same pass.
- Private-by-default; promote to public after license review.
- **Ship criterion:** every existing on-disk corpus is reproducible
  from an HF repo with documented `(language, typeface)`.

### (d) Cut the local-only path  → far-future

- Profiles without `sources:` emit a deprecation warning.
- After one release, `local` stops being the default source.
- Coordinate the `pd-<lang>-<typeface>-<task>-<base>` model-name
  convention with `pdomain-ocr-cli` (the SPA already mints only the new
  form — D-T6).
- **Ship criterion:** production training uses only HF sources.

---

## 3. Multi-source mixing and the model sidecar

When a run's `sources` list has more than one entry, every source
is materialized and concatenated into a transient training dir; a
`WeightedRandomSampler` (recognition / classifier) or per-batch
ratio mixing (detection) applies the per-source `weight`. The model
sidecar's `trained_on[]` array records, per source: `repo`,
`revision`, `rows`, and the **user-asked** `weight` (not the
post-normalization value; see the
[deferred source-weight decision](../docs/context/intent-map.md)).

Concrete adapter/route shapes, error codes, and the dataset-card
block: [`09-hf-integration.md`](09-hf-integration.md) §3–§8.

---

## 4. Deferred choices owned by this milestone

The [shipped HF authority decision](../docs/context/decisions.md), plus the
deferred `hf_default_owner`, source-weight normalization, and LFS quota work in
the [intent map](../docs/context/intent-map.md) — all gated to
M10/M11, none block core parity.

---

## 5. Citations

- Legacy roadmap (HF-datasets, milestones a–d): `pdomain-ocr-training/docs/plans/roadmap.md:84-155`.
- Headline decisions: `roadmap.md:10-19`.
- Model metadata sidecar: `roadmap.md:315-334`.
- Per-row licensing note: `roadmap.md:312-313`.
- SPA adaptation: [`09-hf-integration.md`](09-hf-integration.md),
  [`16-milestones.md`](16-milestones.md) M10–M12.
