"""build_app(settings) factory — wires the FastAPI application."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pd_ocr_trainer_spa._version import __version__
from pd_ocr_trainer_spa.api import env_js

if TYPE_CHECKING:
    from pd_ocr_trainer_spa.settings import Settings

# The compiled SPA lives here (populated by make frontend-build)
_STATIC_DIR = Path(__file__).parent / "static"


def _static_dir() -> Path:
    """Return the static directory path (module-level so tests can patch)."""
    return _STATIC_DIR


def build_app(settings: Settings) -> FastAPI:
    """Construct and return the configured FastAPI application."""
    app = FastAPI(
        title="pd-ocr-trainer-spa",
        version=__version__,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )

    # Store settings on app.state for access by routes
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount pd-ocr-ops suite plumbing: /healthz, /api/suite/*, /api/icons/*
    # Best-effort — the SPA must still start if pd-ocr-ops is unavailable
    try:
        from pd_ocr_ops.suite.routes import mount_routes  # type: ignore[import-untyped]

        mount_routes(app)
    except Exception:  # noqa: BLE001, S110
        # pd-ocr-ops unavailable (e.g. test env without it installed)
        pass

    # Include routers
    app.include_router(env_js.router)

    # SPA catch-all — MUST be last so /api/* routes are not shadowed
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        """Serve the React SPA index.html for any unmatched path."""
        static = _static_dir()
        index = static / "index.html"
        if not index.exists():
            raise HTTPException(
                status_code=503,
                detail="Frontend not built — run make frontend-build",
            )
        return FileResponse(index)

    # Mount static assets directory (check_dir=False: missing dir returns 404, not startup error)
    static = _static_dir()
    if (static / "assets").exists() or True:
        app.mount(
            "/assets",
            StaticFiles(directory=str(static / "assets"), check_dir=False),
            name="assets",
        )

    return app
