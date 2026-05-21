"""build_app(settings) factory — wires the FastAPI application."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pd_ocr_trainer_spa._version import __version__
from pd_ocr_trainer_spa.adapters.builders import (
    build_auth,
    build_dataset_sources,
    build_job_runner,
    build_model_registry,
    build_storage,
)
from pd_ocr_trainer_spa.api import env_js, jobs
from pd_ocr_trainer_spa.core.app_state import AppState
from pd_ocr_trainer_spa.core.errors import AppError
from pd_ocr_trainer_spa.middleware.error_handler import app_error_handler
from pd_ocr_trainer_spa.middleware.request_id import RequestIdMiddleware

if TYPE_CHECKING:
    from pd_ocr_trainer_spa.settings import Settings

# The compiled SPA lives here (populated by make frontend-build)
_STATIC_DIR = Path(__file__).parent / "static"


def _static_dir() -> Path:
    """Return the static directory path (module-level so tests can patch)."""
    return _STATIC_DIR


def _build_app_state(settings: Settings) -> AppState:
    """Construct the AppState adapter bundle and hydrate it from disk."""
    state = AppState(
        settings=settings,
        storage=build_storage(settings),
        auth=build_auth(settings),
        dataset_sources=build_dataset_sources(settings),
        model_registry=build_model_registry(settings),
        job_runner=build_job_runner(settings),
    )
    state.hydrate_from_disk()
    return state


def build_app(settings: Settings) -> FastAPI:
    """Construct and return the configured FastAPI application."""
    app = FastAPI(
        title="pd-ocr-trainer-spa",
        version=__version__,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )

    app.state.settings = settings
    app.state.app_state = _build_app_state(settings)

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppError, app_error_handler)

    # Mount pd-ocr-ops suite plumbing: /healthz, /api/suite/*, /api/icons/*
    # Best-effort — the SPA must still start if pd-ocr-ops is unavailable.
    try:
        from pd_ocr_ops.suite.routes import mount_routes

        mount_routes(app)
    except Exception:  # noqa: BLE001, S110  # optional dep: SPA must boot without pd-ocr-ops
        pass

    app.include_router(env_js.router)
    app.include_router(jobs.router)

    # SPA catch-all — MUST be last so /api/* routes are not shadowed
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        """Serve the React SPA index.html for any unmatched path."""
        del full_path
        static = _static_dir()
        index = static / "index.html"
        if not index.exists():
            raise HTTPException(
                status_code=503,
                detail="Frontend not built — run make frontend-build",
            )
        return FileResponse(index)

    static = _static_dir()
    app.mount(
        "/assets",
        StaticFiles(directory=str(static / "assets"), check_dir=False),
        name="assets",
    )

    return app
