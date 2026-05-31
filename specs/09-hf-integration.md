# 09 — Hugging Face integration

The HF read path (datasets pulled into a local cache for training)
and the HF publish path (datasets / models pushed to repos under
the user's HF namespace). Both wrap `huggingface_hub` and
`datasets`; the SPA never invents new HF concepts.

> Required reading: `pdomain-ocr-training/docs/DATASETS.md` (the
> cross-repo dataset contract — this spec adapts it to the SPA).

---

## 1. Adapter shape

Two adapters, each behind a Protocol from
[`02-backend.md`](02-backend.md) §4:

- `IDatasetSource` — a uniform read API. Two impls: `local` and
  `huggingface`.
- `IModelRegistry` — model list / write / publish. Two impls:
  `filesystem` and `huggingface_hub`. Both can be active
  simultaneously; the publish flow is explicit.

The SPA never silently fans out reads to multiple sources. Every
`Run`'s `args.sources` is an explicit ordered list of
`DatasetSourceRef`s; mixing is the user's choice.

```python
class DatasetSourceRef(BaseModel):
    kind: Literal["local", "huggingface"]
    profile: str | None = None         # required for kind=local
    repo: str | None = None            # required for kind=huggingface; e.g. "ntw8532/pd-ocr-real-ga-clogaelach"
    revision: str | None = None        # tag, branch, or commit; required for huggingface; default "main"
    weight: float = 1.0                # mixing weight; normalized across sources at runner time
```

---

## 2. Authentication

The SPA never prompts the user for an HF token in the UI in v1.
Instead:

- `Settings.hf_token_path` (default `~/.huggingface/token`) is read
  on backend start and exported to subprocesses as `HF_TOKEN`.
- `Settings.hf_default_owner` (e.g. `"ntw8532"`) defaults the
  owner slot of every "create new repo" interaction.
- Missing token → adapter raises `IDatasetSource.AuthError`; SPA
  renders a banner: "HF token not found at `<path>`. Place a token
  there or set `PD_OCR_TRAINER_SPA_HF_TOKEN_PATH`." with a link to
  `pdomain-ocr-training/docs/DATASETS.md#authentication`.
- The token is **never** shipped over the wire to the SPA; the
  frontend has no awareness of its value.

Per memory `feedback_overnight_loops.md`, never invent
metadata: the default owner stays `None` until the user sets it
explicitly. ([Q17](../OPEN_QUESTIONS.md): default to
`Settings.hf_default_owner` from env or refuse to default at all?)

---

## 3. HF dataset-source impl

```python
class HuggingFaceDatasetSource(IDatasetSource):
    name = "huggingface"

    def __init__(self, settings: Settings, hf_api: HfApi):
        ...

    def list(self, profile, task, split):
        ds = datasets.load_dataset(self._repo_for(profile, task), split=split, revision=self._rev_for(...))
        for row in ds:
            yield self._adapt(row, task)

    def fetch_to_local(self, profile, task, split) -> Path:
        # Materialize into a DocTR-compatible directory under hf_cache_dir
        ...
```

Mapping rules (mirrors `pdomain-ocr-training/docs/DATASETS.md` §Dataset shapes):

| HF shape | Internal task | Materialization |
|---|---|---|
| `recognition/v1` (imagefolder + metadata.jsonl) | `recognition` | `<hf_cache_dir>/<repo>@<rev>/recognition/{images/,labels.json}` (write `labels.json` from metadata) |
| `detection/v1` (parquet) | `detection` | `<hf_cache_dir>/<repo>@<rev>/detection/{images/,labels.json}` (decode parquet → labels.json) |
| `typeface-classification/v1` | `typeface-classification` | `<hf_cache_dir>/<repo>@<rev>/typeface/{images/,metadata.jsonl}` (passthrough) |
| `glyph-classification/v1` | `glyph-classification` | `<hf_cache_dir>/<repo>@<rev>/glyph/{images/,metadata.jsonl}` (passthrough) |

Cache dir defaults to `Settings.hf_cache_dir` or `HF_HOME`
(see DATASETS.md §Caching). Hard-linked or copied as needed; the
materialized tree never duplicates pixel bytes when filesystem
hard links work.

---

## 4. Multi-source mixing

When a `Run.args.sources` list has > 1 entry, the runner:

1. Materializes every source via `IDatasetSource.fetch_to_local`.
2. Concatenates them into a single transient training dir under
   `runs/<id>/dataset/`.
3. If `weight` ≠ 1.0 across entries, applies WeightedRandomSampler
   (recognition + classifier) or per-batch ratio mixing
   (detection) — implementation detail in the trainer subprocess.
   The sidecar's `trained_on[].weight` records the user-asked
   weight, not the post-normalization value
   ([Q18](../OPEN_QUESTIONS.md)).

The transient dir is removed on success; preserved on failure for
debugging.

---

## 5. Publish — datasets

```
POST /api/publish/dataset
body: PublishDatasetRequest
→ 202 { run_id, job_id }
```

```python
class PublishDatasetRequest(BaseModel):
    profile: str
    task: TaskEnum
    repo: str                              # owner/name; auto-suggested as "<hf_default_owner>/pd-ocr-real-<lang>-<typeface>"
    visibility: Literal["private", "public"] = "private"
    qualifier: str | None = None           # optional dataset version qualifier (e.g. "2026q2"); appended to repo name slot if needed
    license: str                            # required SPDX identifier — refuses if missing per ROADMAP §License
    notes: str | None = None
```

Server flow:

1. Validate: profile has data, language + typeface set, license is
   a known SPDX value (validated against
   `pdomain_book_tools.licenses.SPDX_VALID_IDS` — bundled list).
2. For each row: confirm per-row `license` field exists in
   `metadata.jsonl` (recognition/typeface/glyph) or per-page
   provenance (detection). Refuse with
   `409 publish.license_missing` if any row lacks it.
3. Compose dataset card (`README.md` with YAML front matter) per
   `DATASETS.md` §Card data block. Owner-set fields (notes,
   license) override; SPA-derived fields (`pd_ocr_shape`,
   `language`, `typeface`, `task_categories`) are mandatory.
4. `huggingface_hub.HfApi.upload_large_folder(...)` invoked; SSE
   relays per-file progress as `JobEvent.progress(current, total,
   message=path)`.
5. On success: writes `runs/<id>/result.json` with
   `{repo, revision, rows_uploaded, dataset_card_url}`.

Idempotency: skipped when local-snapshot hash matches HF tip
revision (per ROADMAP milestone (b)).

---

## 6. Publish — models

```
POST /api/publish/model
body: PublishModelRequest
→ 202 { run_id, job_id }
```

```python
class PublishModelRequest(BaseModel):
    model_name: str                        # must reference an existing TrainedModel
    repo: str                              # owner/name; auto-suggested as "<hf_default_owner>/<model_name>"
    visibility: Literal["private", "public"] = "private"
    notes: str | None = None
```

Server flow:

1. Validate: model exists, sidecar present + complete (or auto-
   regenerate if user opted in), every `trained_on[].repo` is
   either local or a published HF dataset (otherwise
   `409 publish.unpublished_source`).
2. Compose model card from sidecar.
3. `HfApi.upload_folder` for weights + sidecar + config.
4. SSE per-file progress.
5. Writes `ModelPublication` to the in-memory list and stamps the
   sidecar's `published_to` array with the new entry.

Naming rule: rejects legacy-form model names with
`422 publish.legacy_name` — only new-form
`pd-<lang>-<typeface>-<task>-<date>` may publish.

---

## 7. Read-back: HF dataset preview

```
GET /api/sources/huggingface/preview
query: ?repo=ntw8532/...&revision=main&task=recognition&split=train
→ DatasetPreview
```

Returns the first 50 rows in `DatasetView` shape, used by:

- The kanban "Add HF source" dialog before commit.
- The eval form "Use HF source" path.

Cached for 5 min per `(repo, revision)`. Cache invalidated when the
user explicitly clicks "Refresh".

---

## 8. Error codes

| Code | Trigger |
|---|---|
| `hf.auth_missing` | Token absent at startup. Surfaced as a permanent banner. |
| `hf.auth_failed` | 401 from the API. Same banner copy plus the API message. |
| `hf.repo_not_found` | 404 from the API on a repo the user named. |
| `hf.repo_exists` | Trying to create-only a repo that already exists. |
| `hf.shape_mismatch` | A pulled dataset's `card_data.pd_ocr_shape` doesn't match the requested task. |
| `hf.lfs_quota` | LFS quota exceeded mid-upload. ([Q19](../OPEN_QUESTIONS.md)) |
| `publish.license_missing` | At least one row missing `license`. |
| `publish.unpublished_source` | Model trained partially from local data. |
| `publish.legacy_name` | Model's name is in legacy form. |

---

## 9. Acceptance behaviour

1. Set `PD_OCR_TRAINER_SPA_HF_TOKEN_PATH` to a valid token. Open
   `/sources` — list shows `local` (always) and `huggingface`.
2. Open the kanban for `(clogaelach, recognition)` → "Add HF
   source" → enter `ntw8532/pdomain-ocr-synth-ga-clogaelach`. Preview
   shows 50 rows.
3. Start a recognition run with `sources = [local(weight=0.3),
   huggingface(weight=0.7)]`. The transient dataset dir under
   `runs/<id>/dataset/` is built; subprocess runs against it.
   Sidecar's `trained_on` reflects both entries with
   user-supplied weights.
4. Publish the trained model. Validation fires
   `publish.unpublished_source` because the local source isn't
   published. User publishes the local source first; retry succeeds.
5. Publish a recognition dataset with `visibility=private`. Repo
   appears under `<hf_default_owner>` on HF.

---

## 10. Citations

- Cross-repo dataset spec: `pdomain-ocr-training/docs/DATASETS.md`.
- Trainer ROADMAP HF milestones: `pdomain-ocr-training/docs/ROADMAP.md`
  §(a), (b), (c), (d).
- Existing `push_to_hf_hub` codepath: `train_detect.py` and
  `train_recog.py` (search for `push_to_hf_hub`).
