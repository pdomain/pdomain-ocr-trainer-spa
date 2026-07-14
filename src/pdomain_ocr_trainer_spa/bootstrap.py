"""build_app(settings) factory — wires the FastAPI application."""

from __future__ import annotations

import asyncio
import importlib.metadata
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, cast

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

    from pdomain_ops.suite.prefs import PrefsAdapter
    from pdomain_ops.suite.types import InstalledApp

    from pdomain_ocr_trainer_spa.settings import Settings

_PACKAGE = "pdomain_ocr_trainer_spa"

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
        from pdomain_ops.gpu.device_probe import (  # pyright: ignore[reportMissingImports]  # optional API absent from older pdomain-ops wheels
            list_devices,  # pyright: ignore[reportMissingImports]  # optional pre-device-probe API
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


def _build_suite_app() -> InstalledApp:
    """Build the `InstalledApp` descriptor this process registers under.

    Reads the bundled `pdomain-suite.json` fragment and fills in the two
    runtime-only fields, `binary` and `version`, so `mount_routes()` mounts
    device/prefs/update routes under our real `app_id` instead of the
    "unknown" default it falls back to when `suite_app=None`.
    """
    from pdomain_ops.suite.types import InstalledApp

    raw = resources.files(_PACKAGE).joinpath("pdomain-suite.json").read_text(encoding="utf-8")
    fragment = cast("dict[str, object]", json.loads(raw))
    try:
        version = importlib.metadata.version(_PACKAGE)
    except importlib.metadata.PackageNotFoundError:
        version = "0.0.0"
    return InstalledApp.model_validate({**fragment, "binary": sys.executable, "version": version})


def _migrate_unknown_app_prefs(prefs: PrefsAdapter, app_id: str) -> None:
    """One-time migration: recover a compute-device pref stranded under "unknown".

    Before this fix, `mount_routes()` was called with no `suite_app`, so
    `mount_device_routes()` defaulted to `app_id="unknown"` -- any
    compute-device preference a user set persisted under `apps["unknown"]`
    instead of `apps[app_id]`. Copy it over so existing installs don't
    silently lose the setting. `PrefsAdapter` (pdomain_ops.suite.prefs)
    exposes no delete primitive -- only `read`/`write_common`/`write_app` --
    so the stray `compute_device` key is cleared from the "unknown" section
    rather than the section being removed outright.
    """
    snapshot = prefs.read()
    unknown_section = snapshot.apps.get("unknown")
    if not unknown_section:
        return
    stray_device = unknown_section.get("compute_device")
    if not stray_device:
        return
    real_section = dict(snapshot.apps.get(app_id) or {})
    if real_section.get("compute_device"):
        return  # real app key already has an explicit device -- don't clobber it
    real_section["compute_device"] = stray_device
    prefs.write_app(app_id, real_section)
    cleared_unknown = dict(unknown_section)
    del cleared_unknown["compute_device"]
    prefs.write_app("unknown", cleared_unknown)


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
    # suite_app=_build_suite_app() mounts device/prefs/update routes under our
    # real app_id ("pdomain-ocr-trainer-spa") instead of the "unknown" default
    # mount_routes() falls back to with no suite_app -- see its docstring.
    # _migrate_unknown_app_prefs() recovers any compute-device preference
    # stranded under "unknown" by that pre-fix behaviour.
    # Best-effort — the SPA must still start if pdomain-ops is unavailable.
    try:
        from pdomain_ops import SuiteAdapters, mount_routes

        suite_adapters = SuiteAdapters.local()
        suite_app = _build_suite_app()
        _migrate_unknown_app_prefs(suite_adapters.prefs, suite_app.app_id)
        mount_routes(app, suite_adapters, suite_app=suite_app)
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
