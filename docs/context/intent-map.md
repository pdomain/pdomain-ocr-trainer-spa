---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-13
Kind: context
---

# Intent map

## Deferred work

- **Open exports in the labeler.** Add a deep link only after the labeler owns
  a stable project and page URL contract. Owner: pdomain-ocr-labeler-spa, with
  trainer SPA as the consumer.
- **Replace the manifest bridge with PageRecord-backed exchange.** Keep the
  current manifest boundary until both applications can exchange PageRecord
  identity and provenance without importing application-specific behavior.
  Owner: trainer SPA and labeler SPA. Current behavior is documented in
  [labeler import and freshness](../architecture/labeler-import-and-freshness.md).

## Blocked work

- **Glyph-classifier training.** The dataset API intentionally returns 501 for
  glyph classification. End-to-end support is blocked on a typed classifier
  training runner and configuration contract in pdomain-ocr-training. Owner:
  pdomain-ocr-training for the runner; trainer SPA for the UI and orchestration.
