---
Status: active
Owner: CT
Created: 2026-07-13
Last verified: 2026-07-14
Kind: architecture
---

# Labeler import and freshness

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** changing labeler export discovery, kanban freshness, or
  banners.
- **Search terms:** labeler export, manifest, freshness, kanban, dismissal.

The trainer discovers labeler exports through the shared pdomain-ops path
registry, reads their export manifest, and shows newly exported projects as
fresh work. This behavior is optional. The SPA still starts when pdomain-ops or
the export is unavailable.

## Export root selection

An explicit `Settings.labeler_export_root` wins. It can be set with
`PD_OCR_TRAINER_SPA_LABELER_EXPORT_ROOT`. Without one,
`domain/labeler_export.py` asks pdomain-ops for the shared `doctr-export-root`
path. The result records whether the path was configured, discovered, or absent.
The separate legacy `matched_ocr_dir` setting does not select this manifest
export root.

The web process does not scan unrelated directories. This keeps discovery
bounded by the shared path contract.

## Manifest boundary

The trainer consumes `pdomain.doctr-export-manifest` through
`pdomain_ops.schemas.doctr_export`. The manifest is a compatibility bridge
between the labeler export tree and trainer datasets. Missing, corrupt, or
unreadable manifests behave as absent exports instead of failing the kanban
request.

The bridge carries export metadata, not operational page lifecycle. A future
PageRecord integration must preserve that ownership boundary.

## Freshness state

Each profile stores the latest acknowledged project export timestamps in
`profiles/<profile>/freshness_state.json`. A project is fresh when its manifest
timestamp is newer than the stored timestamp. The API and banner builders expose
that state without mutating the manifest. Freshness is acknowledged only after a
successful kanban build. Banner dismissal is separate browser-tab state held in
`sessionStorage`; dismissing a banner does not acknowledge the export.

The export-root mode is returned dynamically by discovery. It is not a static
field on `Settings`.

## Evidence

- Code: `src/pdomain_ocr_trainer_spa/domain/labeler_export.py`,
  `src/pdomain_ocr_trainer_spa/domain/datasets.py`,
  `src/pdomain_ocr_trainer_spa/domain/banners.py`
- Tests: `tests/unit/domain/test_labeler_export.py`,
  `tests/e2e/test_labeler_freshness.py`
- Verified: 2026-07-13 against the current source and tests
