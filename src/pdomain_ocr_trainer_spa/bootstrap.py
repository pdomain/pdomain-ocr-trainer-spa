"""build_app(settings) factory — wires the FastAPI application."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pdomain_ocr_trainer_spa._version import __version__
from pdomain_ocr_trainer_spa.adapters.builders import (
    build_auth,
    build_dataset_sources,
    build_job_runner,
    build_model_registry,
    build_storage,
)
from pdomain_ocr_trainer_spa.api import (
    banners,
    datasets,
    env_js,
    jobs,
    profiles,
    runs,
    sources,
    ui_prefs,
)
from pdomain_ocr_trainer_spa.api import eval as eval_api
from pdomain_ocr_trainer_spa.api import models as models_api
from pdomain_ocr_trainer_spa.api import publish as publish_api
from pdomain_ocr_trainer_spa.core.app_state import AppState
from pdomain_ocr_trainer_spa.core.errors import AppError
from pdomain_ocr_trainer_spa.middleware.error_handler import app_error_handler
from pdomain_ocr_trainer_spa.middleware.request_id import RequestIdMiddleware

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pdomain_ocr_trainer_spa.settings import Settings

# The compiled SPA lives here (populated by make frontend-build)
_STATIC_DIR = Path(__file__).parent / "static"

# Module-level task set — keeps fire-and-forget tasks alive until they complete
# (prevents "Task was destroyed but it is pending!" under CPython's GC).
_background_tasks: set[asyncio.Task[None]] = set()


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


async def _warmup_device_info() -> None:
    """Background probe — pre-populate device cache at startup."""
    try:
        from pdomain_ops.gpu.device_probe import (  # pyright: ignore[reportMissingImports]
            list_devices,  # type: ignore[import-untyped,import-not-found]
        )

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(ThreadPoolExecutor(max_workers=1), list_devices)
    except Exception:  # noqa: BLE001, S110  # optional warmup — never crash startup
        pass


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan: warm up device probe on startup."""
    # Keep a strong reference to the task so it isn't garbage-collected before
    # it completes ("Task was destroyed but it is pending!" guard).
    task = asyncio.create_task(_warmup_device_info())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    yield


def build_app(settings: Settings) -> FastAPI:
    """Construct and return the configured FastAPI application."""
    app = FastAPI(
        title="pdomain-ocr-trainer-spa",
        version=__version__,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
        lifespan=_lifespan,
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

    # Mount pdomain-ops suite plumbing: /healthz, /api/suite/*, /api/icons/*
    # Best-effort — the SPA must still start if pdomain-ops is unavailable.
    try:
        from pdomain_ops.suite.routes import mount_routes

        mount_routes(app)
    except Exception:  # noqa: BLE001, S110  # optional dep: SPA must boot without pdomain-ops
        pass

    app.include_router(env_js.router)
    app.include_router(banners.router)
    app.include_router(jobs.router)
    app.include_router(profiles.router)
    app.include_router(datasets.router)
    app.include_router(datasets._diag_router)
    app.include_router(runs.router)
    app.include_router(models_api.router)
    app.include_router(eval_api.router)
    app.include_router(sources.router)
    app.include_router(publish_api.router)
    app.include_router(ui_prefs.router)

    # Static assets — MUST be mounted before the SPA catch-all
    static = _static_dir()
    app.mount(
        "/assets",
        StaticFiles(directory=str(static / "assets"), check_dir=False),
        name="assets",
    )

    # SPA catch-all — MUST be last so /api/* routes and /assets/* are not shadowed
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        """Serve the React SPA index.html for any unmatched path."""
        del full_path
        index = _static_dir() / "index.html"
        if not index.exists():
            raise HTTPException(
                status_code=503,
                detail="Frontend not built — run make frontend-build",
            )
        return FileResponse(index)

    return app
