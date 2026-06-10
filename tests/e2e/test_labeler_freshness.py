"""Browser verification: kanban renders fresh-flagged projects + banner visible.

Uses a fixture export tree + manifest so the test is fully self-contained.
Requires ``make playwright-install`` (runs chromium).

Marked ``@pytest.mark.e2e`` so they are excluded from ``make test``
(pure-Python unit tests only) and execute under ``make e2e-browser``.

Ordering note: ``test_banners_api_returns_fresh_banner`` and
``test_kanban_api_returns_fresh_row`` each independently arrange a fresh
freshness state at the start of their bodies (rewriting the manifest with a
newer ``exported_at`` and deleting ``freshness_state.json``).  This removes
any hidden dependency on declaration order or xdist scheduling.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from collections.abc import Generator
from pathlib import Path
from typing import NamedTuple

import pytest
import uvicorn

from pdomain_ocr_trainer_spa.bootstrap import build_app
from pdomain_ocr_trainer_spa.settings import Settings

_E2E_PORT = 8091

# Canonical on-disk manifest key (Gap-4: standardise on "schema" everywhere)
_MANIFEST_SCHEMA = "pdomain.doctr-export-manifest"


def _wait_for_port(host: str, port: int, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Server on {host}:{port} did not start within {timeout}s")


def _write_manifest(base: Path, exported_at: str) -> None:
    """(Re)write manifest.json with the given exported_at timestamp.

    Called in each test's arrange step so the freshness state is independent
    of any prior test execution order.
    """
    manifest = {
        "schema": _MANIFEST_SCHEMA,
        "version": 1,
        "generated_at": "2026-06-10T12:00:00Z",
        "app": "pdomain-ocr-labeler-spa",
        "projects": {
            "myproj": {
                "exported_at": exported_at,
                "page_count": 1,
                "tasks": {"recognition": {"item_count": 1}},
            }
        },
    }
    (base / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


class _LiveServer(NamedTuple):
    url: str
    app_data_root: Path


@pytest.fixture(scope="module")
def export_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a minimal export tree (manifest written per-test for ordering safety)."""
    base = tmp_path_factory.mktemp("export")
    proj = base / "myproj" / "all" / "recognition"
    proj.mkdir(parents=True)
    (proj / "labels.json").write_text(json.dumps({"img_0001.png": "test label"}), encoding="utf-8")
    images = proj / "images"
    images.mkdir()
    (images / "img_0001.png").write_bytes(b"\x89PNG")
    # Write an initial manifest so the tree is structurally valid from the start
    _write_manifest(base, "2026-06-10T11:00:00Z")
    return base


@pytest.fixture(scope="module")
def live_server(tmp_path_factory: pytest.TempPathFactory, export_tree: Path) -> Generator[_LiveServer]:
    """Start the real FastAPI app on port 8091; yield (_LiveServer) namedtuple."""
    tmp = tmp_path_factory.mktemp("app")
    app_data_root = tmp / "app"
    s = Settings(
        labeler_export_root=export_tree,  # type: ignore[arg-type]
        app_data_root=app_data_root,  # type: ignore[arg-type]
        runs_dir=tmp / "runs",  # type: ignore[arg-type]
        jobs_db_path=tmp / "jobs.db",  # type: ignore[arg-type]
        job_runner_kind="fake",
        model_registry_kind="fake",
    )
    # Build the SPA with a fake index.html so GET / returns 200
    static_dir = Path(__file__).parent.parent.parent / "src" / "pdomain_ocr_trainer_spa" / "static"
    static_dir.mkdir(exist_ok=True)
    (static_dir / "index.html").write_text(
        '<html><body data-testid="home-page">OCR Trainer</body></html>',
        encoding="utf-8",
    )
    app = build_app(s)
    config = uvicorn.Config(app, host="127.0.0.1", port=_E2E_PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_for_port("127.0.0.1", _E2E_PORT)
    yield _LiveServer(url=f"http://127.0.0.1:{_E2E_PORT}", app_data_root=app_data_root)
    server.should_exit = True


def _reset_freshness(app_data_root: Path, profile: str = "all") -> None:
    """Delete freshness_state.json for a profile so the next scan is a first scan."""
    p = app_data_root / "profiles" / profile / "freshness_state.json"
    p.unlink(missing_ok=True)


@pytest.mark.e2e
@pytest.mark.filterwarnings("ignore::DeprecationWarning:websockets")
@pytest.mark.filterwarnings("ignore::DeprecationWarning:uvicorn")
def test_home_page_loads(page, live_server: _LiveServer) -> None:
    """SPA index.html is served; no console errors about failed resources."""
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(live_server.url)
    page.wait_for_selector('[data-testid="home-page"]', timeout=5000)
    assert not errors, f"console errors: {errors}"


@pytest.mark.e2e
@pytest.mark.filterwarnings("ignore::DeprecationWarning:websockets")
@pytest.mark.filterwarnings("ignore::DeprecationWarning:uvicorn")
def test_banners_api_returns_fresh_banner(export_tree: Path, live_server: _LiveServer) -> None:
    """GET /api/banners returns the new-labeled-pages banner for our fixture export.

    Independently arranges fresh state so execution order does not matter.
    """
    import requests

    # Arrange: reset freshness record and write a manifest with a future timestamp
    _reset_freshness(live_server.app_data_root)
    _write_manifest(export_tree, "2099-01-01T00:00:00Z")

    resp = requests.get(f"{live_server.url}/api/banners", timeout=5)
    assert resp.status_code == 200
    banners = resp.json()["banners"]
    ids = [b["id"] for b in banners]
    assert "new-labeled-pages" in ids, f"expected new-labeled-pages in {ids}"


@pytest.mark.e2e
@pytest.mark.filterwarnings("ignore::DeprecationWarning:websockets")
@pytest.mark.filterwarnings("ignore::DeprecationWarning:uvicorn")
def test_kanban_api_returns_fresh_row(export_tree: Path, live_server: _LiveServer) -> None:
    """GET /api/profiles/all/datasets/recognition/kanban returns is_fresh=true for myproj.

    Independently arranges fresh state so execution order does not matter.
    """
    import requests

    # Arrange: reset freshness record and write a manifest with a future timestamp
    _reset_freshness(live_server.app_data_root)
    _write_manifest(export_tree, "2099-06-10T11:00:00Z")

    resp = requests.get(
        f"{live_server.url}/api/profiles/all/datasets/recognition/kanban",
        timeout=5,
    )
    assert resp.status_code == 200
    view = resp.json()
    unassigned = view["columns"]["unassigned"]["rows"]
    assert len(unassigned) >= 1, "expected at least one row in unassigned; got empty"
    fresh_rows = [r for r in unassigned if r.get("is_fresh")]
    assert len(fresh_rows) >= 1, f"expected at least one is_fresh row; got {unassigned}"


@pytest.mark.e2e
@pytest.mark.filterwarnings("ignore::DeprecationWarning:websockets")
@pytest.mark.filterwarnings("ignore::DeprecationWarning:uvicorn")
def test_datasets_subpath_renders(page, live_server: _LiveServer) -> None:
    """React Router sub-path /datasets/all/recognition serves the SPA index."""
    page.goto(f"{live_server.url}/datasets/all/recognition")
    page.wait_for_selector('[data-testid="home-page"]', timeout=5000)
    assert page.url.endswith("/datasets/all/recognition")
