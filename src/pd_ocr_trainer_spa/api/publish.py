"""api/publish.py — HF publish endpoints (spec 09 §5–§6, M11).

Routes:
    POST /api/publish/dataset
        Body: PublishDatasetRequest
        Returns: 202 { run_id, job_id }

    POST /api/publish/model
        Body: PublishModelRequest
        Returns: 202 { run_id, job_id }

Authentication: reads Settings.hf_token_path — missing → 400 hf.auth_missing.
License gating: unrecognised SPDX → 409 publish.license_missing.
Legacy model names: → 422 publish.legacy_name.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from pd_ocr_trainer_spa.api.sources import _require_hf_token
from pd_ocr_trainer_spa.core.app_state import get_app_state
from pd_ocr_trainer_spa.core.enums import TaskEnum  # noqa: TC001 — pydantic resolves at model-build time
from pd_ocr_trainer_spa.core.errors import AppError
from pd_ocr_trainer_spa.domain import models as dom_models
from pd_ocr_trainer_spa.domain import publish as dom

if TYPE_CHECKING:
    from pd_ocr_trainer_spa.core.app_state import AppState

router = APIRouter(prefix="/api/publish", tags=["publish"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class PublishDatasetRequest(BaseModel):
    """Body for POST /api/publish/dataset (spec 09 §5)."""

    profile: str
    task: TaskEnum
    repo: str
    visibility: Literal["private", "public"] = "private"
    qualifier: str | None = None
    license: str  # required SPDX identifier
    notes: str | None = None


class PublishModelRequest(BaseModel):
    """Body for POST /api/publish/model (spec 09 §6)."""

    model_name: str
    repo: str
    visibility: Literal["private", "public"] = "private"
    notes: str | None = None


class PublishResponse(BaseModel):
    """202 response for publish endpoints."""

    run_id: str
    job_id: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/dataset", status_code=202)
async def publish_dataset(
    body: PublishDatasetRequest,
    state: AppState = Depends(get_app_state),
) -> PublishResponse:
    """Publish a labelled dataset to HuggingFace (spec 09 §5).

    1. Validates HF token.
    2. Validates license SPDX id.
    3. Submits an async publish job.
    Returns 202 with run_id + job_id on success.
    """
    token = _require_hf_token(state.settings)  # raises 400 hf.auth_missing
    dom.validate_spdx_license(body.license)      # raises 409 publish.license_missing

    run_id, job_id = dom.submit_publish_dataset_job(
        settings=state.settings,
        token=token,
        profile=body.profile,
        task=body.task.value,
        repo=body.repo,
        visibility=body.visibility,
        license_id=body.license,
        qualifier=body.qualifier,
        notes=body.notes,
    )
    return PublishResponse(run_id=run_id, job_id=job_id)


@router.post("/model", status_code=202)
async def publish_model(
    body: PublishModelRequest,
    state: AppState = Depends(get_app_state),
) -> PublishResponse:
    """Publish a trained model to HuggingFace (spec 09 §6).

    1. Validates HF token.
    2. Resolves model — 404 if absent.
    3. Rejects legacy-form model names with 422 publish.legacy_name.
    4. Submits an async publish job.
    Returns 202 with run_id + job_id on success.
    """
    token = _require_hf_token(state.settings)  # raises 400 hf.auth_missing

    # Resolve the model from the filesystem registry — 404 if absent.
    model = dom_models.get_model(state.settings, body.model_name)

    # Reject legacy-form model names (spec 09 §6).
    parsed = dom_models.parse_model_name(model.name)
    if parsed.is_legacy:
        raise AppError(
            code="publish.legacy_name",
            message=(
                f"Model '{model.name}' uses a legacy name form and cannot be published. "
                "Rename it to pd-{lang}-{typeface}-{task}[-{qualifier}] first."
            ),
            status_code=422,
        )

    run_id, job_id = dom.submit_publish_model_job(
        settings=state.settings,
        token=token,
        model_name=body.model_name,
        repo=body.repo,
        visibility=body.visibility,
        notes=body.notes,
    )
    return PublishResponse(run_id=run_id, job_id=job_id)
