"""Health check shim — /healthz is owned by pdomain-ops mount_routes.

This module is a placeholder for any SPA-specific readiness probe
that may be added in a future milestone.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/healthz-spa", include_in_schema=False)
async def healthz_spa() -> dict[str, str]:
    """SPA-specific health probe (reserved for future use)."""
    return {"status": "ok"}
