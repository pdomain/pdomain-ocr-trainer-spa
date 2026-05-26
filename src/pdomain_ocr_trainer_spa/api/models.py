"""api/models.py — trained-model registry REST surface (spec 08-models §5).

Routes:

* ``GET    /api/models``                          — list trained models
* ``GET    /api/models/{name}``                   — one model
* ``GET    /api/models/{name}/sidecar``           — the raw sidecar
* ``POST   /api/models/{name}/regenerate-sidecar`` — rebuild a missing sidecar
* ``PATCH  /api/models/{name}``                   — patch sidecar metadata
* ``DELETE /api/models/{name}``                   — delete the leaf dir
* ``POST   /api/models/{name}/rename``            — rename leaf dir + sidecar
* ``POST   /api/models/scan``                     — force a registry refresh

The registry is filesystem-backed; this router never imports torch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from pdomain_ocr_trainer_spa.core.app_state import get_app_state
from pdomain_ocr_trainer_spa.core.enums import TaskEnum  # noqa: TC001 — pydantic resolves at model-build time
from pdomain_ocr_trainer_spa.core.models import (  # noqa: TC001 — pydantic resolves at model-build time
    ModelSidecar,
    TrainedModel,
)
from pdomain_ocr_trainer_spa.domain import models as dom

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.core.app_state import AppState

router = APIRouter(prefix="/api/models", tags=["models"])


class ModelListItem(BaseModel):
    """One row of ``GET /api/models`` — a model plus its sidecar-presence flag."""

    model: TrainedModel
    has_sidecar: bool
    is_legacy: bool


class ModelListResponse(BaseModel):
    """Envelope for ``GET /api/models``."""

    models: list[ModelListItem]


class PatchModelRequest(BaseModel):
    """Body for ``PATCH /api/models/{name}`` (spec 08 §5)."""

    language: str | None = None
    typeface: str | None = None
    qualifier: str | None = None


class RenameModelRequest(BaseModel):
    """Body for ``POST /api/models/{name}/rename`` (spec 08 §5)."""

    new_name: str


def _to_item(settings: object, model: TrainedModel) -> ModelListItem:
    return ModelListItem(
        model=model,
        has_sidecar=dom.has_sidecar(model),
        is_legacy=dom.parse_model_name(model.name).is_legacy,
    )


@router.get("")
async def list_models(
    profile: str | None = None,
    task: TaskEnum | None = None,
    include_legacy: bool = True,
    state: AppState = Depends(get_app_state),
) -> ModelListResponse:
    """List every discovered trained model (spec 08 §6)."""
    models = dom.list_models(
        state.settings,
        profile=profile,
        task=task,
        include_legacy=include_legacy,
    )
    return ModelListResponse(
        models=[_to_item(state.settings, m) for m in models]
    )


@router.post("/scan")
async def scan_models(
    state: AppState = Depends(get_app_state),
) -> ModelListResponse:
    """Force a fresh filesystem walk of the model registry (spec 08 §8)."""
    return await list_models(state=state)


@router.get("/{name}")
async def get_model(
    name: str,
    state: AppState = Depends(get_app_state),
) -> ModelListItem:
    """Return one trained model by name (404 if absent)."""
    model = dom.get_model(state.settings, name)
    return _to_item(state.settings, model)


@router.get("/{name}/sidecar")
async def get_model_sidecar(
    name: str,
    state: AppState = Depends(get_app_state),
) -> ModelSidecar:
    """Return the raw sidecar for a model (spec 08 §5)."""
    return dom.get_model(state.settings, name).sidecar


@router.post("/{name}/regenerate-sidecar")
async def regenerate_sidecar(
    name: str,
    state: AppState = Depends(get_app_state),
) -> ModelListItem:
    """Rebuild a missing or stale sidecar from disk + the matching run (spec 08 §4)."""
    model = dom.regenerate_sidecar(state.settings, name)
    return _to_item(state.settings, model)


@router.patch("/{name}")
async def patch_model(
    name: str,
    body: PatchModelRequest,
    state: AppState = Depends(get_app_state),
) -> ModelListItem:
    """Patch a model's sidecar metadata — no on-disk rename (spec 08 §5)."""
    model = dom.patch_model(
        state.settings,
        name,
        language=body.language,
        typeface=body.typeface,
        qualifier=body.qualifier,
    )
    return _to_item(state.settings, model)


@router.delete("/{name}", status_code=204)
async def delete_model(
    name: str,
    state: AppState = Depends(get_app_state),
) -> None:
    """Delete a model's leaf directory (409 if a non-terminal run references it)."""
    dom.delete_model(state.settings, name)


@router.post("/{name}/rename")
async def rename_model(
    name: str,
    body: RenameModelRequest,
    state: AppState = Depends(get_app_state),
) -> ModelListItem:
    """Rename a model's leaf dir + sidecar (spec 08 §5)."""
    model = dom.rename_model(state.settings, name, body.new_name)
    return _to_item(state.settings, model)
