# Lint Deviations

This document records intentional suppressions of static-analysis warnings
that are approved by convention. Each entry names the rule, the tool, the
affected files, and the justification.

---

## `domain/labeler_export.py`: optional pdomain-ops Track-B imports

- **Rules:** `reportMissingImports` (basedpyright), `no-redef` / `misc`
  (pyright type: ignore annotations)
- **Tool:** basedpyright + pyright type annotations
- **Files:** `src/pdomain_ocr_trainer_spa/domain/labeler_export.py`
- **Justification:** Track B (`pdomain-ops`) adds `resolve_shared_path` and
  `DoctrExportManifest` / `read_manifest`. The SPA must boot with a pre-Track-B
  wheel installed; the `try/except ImportError` guard plus fallback stubs is the
  approved pattern. Inline `# pyright: ignore[...]` and `# type: ignore[...]`
  comments name the suppressed codes at each deviation site.
