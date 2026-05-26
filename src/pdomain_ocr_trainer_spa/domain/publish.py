"""domain/publish.py - HF publish domain logic (spec 09 §5-§6, M11).

Responsibilities:
- SPDX license validation delegated to ``pdomain_book_tools.licenses`` (spec 09 §5).
- Stub job-submission helpers used by api/publish.py; the real async worker
  path is wired the same way as training runs via LongJobRunner.
- License-gating: refuses publish when ``license`` field is not a known SPDX id.
"""

from __future__ import annotations

from pdomain_book_tools.licenses import SPDX_VALID_IDS, is_valid_spdx_id

from pdomain_ocr_trainer_spa.core.errors import AppError

# Re-export so callers that import SPDX_VALID_IDS from this module still work,
# and so the object-identity assertion in tests can verify the delegation.
__all__ = ["SPDX_VALID_IDS", "validate_spdx_license"]


def validate_spdx_license(license_id: str) -> None:
    """Raise 409 publish.license_missing when *license_id* is not a known SPDX id.

    Matching uses ``pdomain_book_tools.licenses.is_valid_spdx_id``, which is
    case-sensitive and exact — ``Apache-2.0`` is valid, ``apache-2.0`` is not.
    Callers should supply canonical-case SPDX identifiers.
    """
    if not is_valid_spdx_id(license_id):
        raise AppError(
            code="publish.license_missing",
            message=(
                f"License '{license_id}' is not a recognised SPDX identifier. "
                "Provide a valid SPDX id (e.g. 'Apache-2.0', 'CC-BY-4.0')."
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
    from pdomain_ocr_trainer_spa.core.errors import AdapterNotImplementedError

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
    from pdomain_ocr_trainer_spa.core.errors import AdapterNotImplementedError

    raise AdapterNotImplementedError(
        "Model publish worker not yet implemented. "
        "Wire a worker script in a follow-on milestone."
    )
