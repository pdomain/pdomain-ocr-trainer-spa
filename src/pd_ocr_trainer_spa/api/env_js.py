"""GET /env.js — inlines build version and feature flags for the SPA."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import Response

from pd_ocr_trainer_spa._version import __version__

router = APIRouter()


@router.get("/env.js", include_in_schema=False)
async def env_js(request: Request) -> Response:
    """Return a JS snippet that sets window.__APP_ENV__ for the SPA."""
    settings = getattr(request.app.state, "settings", None)
    features: dict[str, bool] = {}
    if settings is not None:
        features = {
            "enableTypefaceTraining": settings.enable_typeface_training,
            "enableGlyphTraining": settings.enable_glyph_training,
            "enableHfPublish": settings.enable_hf_publish,
        }
    payload = json.dumps({"version": __version__, "features": features})
    content = f"window.__APP_ENV__ = {payload};\n"
    return Response(content=content, media_type="application/javascript")
