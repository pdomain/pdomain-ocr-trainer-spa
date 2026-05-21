"""api/profiles.py — profile CRUD REST surface (spec 02 §4.3, spec 04)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from pd_ocr_trainer_spa.core.app_state import get_app_state
from pd_ocr_trainer_spa.core.enums import TypefaceEnum  # noqa: TC001 — pydantic resolves at model-build time
from pd_ocr_trainer_spa.core.models import Profile  # noqa: TC001 — pydantic resolves at model-build time
from pd_ocr_trainer_spa.domain import profiles as dom

if TYPE_CHECKING:
    from pd_ocr_trainer_spa.core.app_state import AppState

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


class CreateProfileRequest(BaseModel):
    """Body for ``POST /api/profiles`` (spec 04 §1.3)."""

    name: str
    display_name: str | None = None
    language: str | None = None
    typeface: TypefaceEnum | None = None
    notes: str | None = None


class UpdateProfileRequest(BaseModel):
    """Body for ``PATCH /api/profiles/{name}`` — omitted keys are untouched (spec 04 §1.4)."""

    display_name: str | None = None
    language: str | None = None
    typeface: TypefaceEnum | None = None
    notes: str | None = None


class ProfileListResponse(BaseModel):
    """Envelope for ``GET /api/profiles``."""

    profiles: list[Profile]
    has_legacy_layout: bool


@router.get("")
async def list_profiles(
    state: AppState = Depends(get_app_state),
) -> ProfileListResponse:
    """List every discovered profile plus the legacy-layout flag (spec 04 §6.1)."""
    return ProfileListResponse(
        profiles=dom.list_profiles(state.settings),
        has_legacy_layout=dom.has_legacy_layout(state.settings),
    )


@router.post("", status_code=201)
async def create_profile(
    body: CreateProfileRequest,
    state: AppState = Depends(get_app_state),
) -> Profile:
    """Create a profile and its dataset directories (spec 04 §1.3)."""
    return dom.create_profile(
        state.settings,
        name=body.name,
        display_name=body.display_name,
        language=body.language,
        typeface=body.typeface,
        notes=body.notes,
    )


@router.get("/{name}")
async def get_profile(
    name: str,
    state: AppState = Depends(get_app_state),
) -> Profile:
    """Return one profile by normalized name (404 if absent)."""
    return dom.get_profile(state.settings, name)


@router.patch("/{name}")
async def update_profile(
    name: str,
    body: UpdateProfileRequest,
    state: AppState = Depends(get_app_state),
) -> Profile:
    """Patch profile metadata; explicit ``null`` clears a field (spec 04 §1.4)."""
    fields = body.model_dump(exclude_unset=True)
    return dom.update_profile(state.settings, name, fields=fields)


@router.delete("/{name}", status_code=204)
async def delete_profile(
    name: str,
    state: AppState = Depends(get_app_state),
) -> None:
    """Delete a profile (409 for ``all`` or any profile holding data)."""
    dom.delete_profile(state.settings, name)


@router.post("/migrate-legacy", status_code=204)
async def migrate_legacy(
    state: AppState = Depends(get_app_state),
) -> None:
    """Migrate the legacy flat layout into ``all/`` — idempotent (spec 04 §1.6)."""
    dom.migrate_legacy(state.settings)
