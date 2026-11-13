---
Status: active
Owner: CT
Created: 2026-11-12
Last verified: 2026-11-13
Kind: architecture
---

# Hugging Face read and publish

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** changing dataset preview, publish, or the HF token.
- **Search terms:** hf_token_path, enable_hf_publish, publish dataset, preview

Remote dataset preview exists, and the publish routes validate the request
and then refuse to start a job.

Preview and the publish routes share a token file.

The publish feature flag is emitted to the browser.

The flag does not gate the routes.

## Token path: None, missing file, or unreadable

`PD_OCR_TRAINER_SPA_HF_TOKEN_PATH` sets `Settings.hf_token_path`.

When the path is `None`, the missing-token banner stays off. Preview and
publish return 400 `hf.auth_missing`.

When the path is set and the file is missing, the banner fires (`hf-token-missing`).
Preview and publish return the same 400 `hf.auth_missing`.

A file that exists but cannot be read raises from `read_text`. That case is
not the 400, and it does not show the banner.

The adapter receives the token string. It does not open the token file
itself.

## Preview reads a remote dataset and does not publish

`GET /api/sources/huggingface/preview` reads a remote dataset preview. A
successful read does not publish anything. Preview reads at most 50 rows of
`metadata.jsonl`; `total` is the number returned, not a remote dataset count.
Task and split do not select different remote files. Missing optional Hub
support and remote/read failures can return an empty preview.

Publish is a different router.

## Publish validates the request, then refuses to start

`POST /api/publish/dataset` and `POST /api/publish/model` are mounted.

The page is `/publish`.

Dataset publish checks the token, then checks the license with
`pdomain_book_tools.licenses`. An unknown SPDX id returns 409
`publish.license_missing`.

After checking the token, model publish calls `get_model`. An unknown name is 404
`model.unknown`. A stored legacy name then returns 422
`publish.legacy_name`.

The handlers then call `submit_publish_dataset_job` or
`submit_publish_model_job`. Both functions raise
`AdapterNotImplementedError`. The message says the publish worker is not
implemented.

There is no branch for a fake runner in `submit_publish_dataset_job` or
`submit_publish_model_job`, despite the docstring.

The filesystem model registry's `publish` method raises the same error,
`AdapterNotImplementedError`.

`HuggingFaceHubModelRegistry` raises on every method.

### enable_hf_publish does not, by itself, block or allow a publish request

`enable_hf_publish` defaults to false. `/env.js` copies it to
`enableHfPublish`.

No React module reads that flag. The publish route handlers do not read it
either.

The setting does not, by itself, block or allow a publish request.

### Empty owner fill and the LFS quota message are deferred

Filling an empty owner from the token identity, and mapping LFS quota errors
to a specific UI message, are still deferred. See the
[roadmap](../roadmap.md).

`hf_default_owner` and `hf_cache_dir` are settings.

## Files read on 2026-11-12; tests were not rerun

- Code: `src/pdomain_ocr_trainer_spa/domain/publish.py`,
  `src/pdomain_ocr_trainer_spa/api/sources.py`,
  `src/pdomain_ocr_trainer_spa/api/publish.py`,
  `src/pdomain_ocr_trainer_spa/adapters/model_registry/huggingface_hub.py`,
  `src/pdomain_ocr_trainer_spa/api/env_js.py`,
  `src/pdomain_ocr_trainer_spa/settings.py`,
  `src/pdomain_ocr_trainer_spa/domain/banners.py`,
  `src/pdomain_ocr_trainer_spa/adapters/dataset_sources/huggingface.py`
- Tests: `tests/integration/api/test_publish.py`,
  `tests/integration/api/test_banners.py`,
  `tests/unit/domain/test_banners.py`
- Verified: 2026-11-12 by reading those files and searching the frontend for
  `enableHfPublish`. Tests were not rerun.
