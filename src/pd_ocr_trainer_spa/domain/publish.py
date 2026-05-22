"""domain/publish.py — HF publish domain logic (spec 09 §5–§6, M11).

Responsibilities:
- SPDX license validation (bundled list — a minimal common subset).
- Stub job-submission helpers used by api/publish.py; the real async worker
  path is wired the same way as training runs via LongJobRunner.
- License-gating: refuses publish when ``license`` field is not a known SPDX id.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pd_ocr_trainer_spa.core.errors import AppError

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# SPDX license allowlist (common subset — spec 09 §5 references
# pd_book_tools.licenses.SPDX_VALID_IDS which does not yet exist; we bundle
# a commonly-used subset until pd-book-tools exposes it).
# ---------------------------------------------------------------------------

#: Normalised lower-case SPDX identifiers accepted by the publish endpoint.
#: Extend this list as needed; keep sorted for readability.
SPDX_VALID_IDS: frozenset[str] = frozenset(
    {
        "agpl-3.0",
        "apache-2.0",
        "bsd-2-clause",
        "bsd-3-clause",
        "cc-by-4.0",
        "cc-by-nc-4.0",
        "cc-by-nc-nd-4.0",
        "cc-by-nc-sa-4.0",
        "cc-by-nd-4.0",
        "cc-by-sa-4.0",
        "cc0-1.0",
        "eupl-1.2",
        "gpl-2.0",
        "gpl-2.0-only",
        "gpl-3.0",
        "gpl-3.0-only",
        "lgpl-2.1",
        "lgpl-3.0",
        "mit",
        "mpl-2.0",
        "odc-by",
        "odbl",
        "unlicense",
    }
)


def validate_spdx_license(license_id: str) -> None:
    """Raise 409 publish.license_missing when *license_id* is not a known SPDX id.

    Comparison is case-insensitive to be generous with user input.
    """
    if license_id.lower().strip() not in SPDX_VALID_IDS:
        raise AppError(
            code="publish.license_missing",
            message=(
                f"License '{license_id}' is not a recognised SPDX identifier. "
                "Provide a valid SPDX id (e.g. 'apache-2.0', 'cc-by-4.0')."
            ),
            status_code=409,
        )


def submit_publish_dataset_job(
    settings: object,
    token: str,
    profile: str,
    task: str,
    repo: str,
    visibility: str,
    license_id: str,
    qualifier: str | None,
    notes: str | None,
) -> tuple[str, str]:
    """Submit a dataset publish job via the job runner.

    Returns *(run_id, job_id)*.

    This implementation is a thin wrapper that creates a ``publish`` run record
    and delegates to the ``LongJobRunner`` — the same seam used by training runs.
    For now, because publish workers are deferred, we raise
    ``AdapterNotImplementedError`` unless a fake runner is configured.
    """
    # Import lazily to stay torch-free at module-load time.
    from pd_ocr_trainer_spa.core.errors import AdapterNotImplementedError

    raise AdapterNotImplementedError(
        "Dataset publish worker not yet implemented. "
        "Wire a worker script in a follow-on milestone."
    )


def submit_publish_model_job(
    settings: object,
    token: str,
    model_name: str,
    repo: str,
    visibility: str,
    notes: str | None,
) -> tuple[str, str]:
    """Submit a model publish job via the job runner.

    Returns *(run_id, job_id)*.

    Same deferral as ``submit_publish_dataset_job``.
    """
    from pd_ocr_trainer_spa.core.errors import AdapterNotImplementedError

    raise AdapterNotImplementedError(
        "Model publish worker not yet implemented. "
        "Wire a worker script in a follow-on milestone."
    )
