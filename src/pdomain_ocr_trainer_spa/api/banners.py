"""api/banners.py — environment-banner REST surface (spec 11-notifications §3).

Single route::

    GET /api/banners  -> {"banners": [Banner, ...]}

The list is synthesised on every request from environment checks; no
banner state is persisted server-side.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from pdomain_ocr_trainer_spa.core.app_state import get_app_state
from pdomain_ocr_trainer_spa.domain import datasets as datasets_dom
from pdomain_ocr_trainer_spa.domain.banners import Banner, synthesize_banners

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.core.app_state import AppState

router = APIRouter(prefix="/api/banners", tags=["banners"])


class BannerListResponse(BaseModel):
    """Response body for ``GET /api/banners``."""

    banners: list[Banner]


@router.get("", response_model=BannerListResponse)
async def list_banners(
    state: AppState = Depends(get_app_state),
) -> BannerListResponse:
    """Return the active environment banners for the current app state (Track D: includes freshness)."""
    fresh_count = datasets_dom.count_fresh_projects(state.settings)
    return BannerListResponse(banners=synthesize_banners(state.settings, fresh_project_count=fresh_count))
