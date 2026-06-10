"""Browser verification: kanban renders fresh-flagged projects + banner visible.

Uses a fixture export tree + manifest so the test is fully self-contained.
Requires ``make playwright-install`` (runs chromium).

Marked ``@pytest.mark.e2e`` so they are excluded from ``make test``
(pure-Python unit tests only) and execute under ``make e2e-browser``.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from collections.abc import Generator
from pathlib import Path

import pytest
import uvicorn

from pdomain_ocr_trainer_spa.bootstrap import build_app
from pdomain_ocr_trainer_spa.settings import Settings

_E2E_PORT = 8091


def _wait_for_port(host: str, port: int, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Server on {host}:{port} did not start within {timeout}s")


@pytest.fixture(scope="module")
def export_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a minimal export tree with a manifest for 'myproj'."""
    base = tmp_path_factory.mktemp("export")
    proj = base / "myproj" / "all" / "recognition"
    proj.mkdir(parents=True)
    (proj / "labels.json").write_text(json.dumps({"img_0001.png": "test label"}), encoding="utf-8")
    images = proj / "images"
    images.mkdir()
    (images / "img_0001.png").write_bytes(b"\x89PNG")
    manifest = {
        "schema_id": "pdomain.doctr-export-manifest",
        "version": 1,
        "generated_at": "2026-06-10T12:00:00Z",
        "app": "pdomain-ocr-labeler-spa",
        "projects": {
            "myproj": {
                "exported_at": "2026-06-10T11:00:00Z",
                "page_count": 1,
                "tasks": {"recognition": {"item_count": 1}},
            }
        },
    }
    (base / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return base


@pytest.fixture(scope="module")
def live_server(tmp_path_factory: pytest.TempPathFactory, export_tree: Path) -> Generator[str]:
    """Start the real FastAPI app on port 8091; yield the base URL."""
    tmp = tmp_path_factory.mktemp("app")
    s = Settings(
        labeler_export_root=export_tree,  # type: ignore[arg-type]
        app_data_root=tmp / "app",  # type: ignore[arg-type]
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
    yield f"http://127.0.0.1:{_E2E_PORT}"
    server.should_exit = True


@pytest.mark.e2e
@pytest.mark.filterwarnings("ignore::DeprecationWarning:websockets")
@pytest.mark.filterwarnings("ignore::DeprecationWarning:uvicorn")
def test_home_page_loads(page, live_server: str) -> None:
    """SPA index.html is served; no console errors about failed resources."""
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(live_server)
    page.wait_for_selector('[data-testid="home-page"]', timeout=5000)
    assert not errors, f"console errors: {errors}"


@pytest.mark.e2e
@pytest.mark.filterwarnings("ignore::DeprecationWarning:websockets")
@pytest.mark.filterwarnings("ignore::DeprecationWarning:uvicorn")
def test_banners_api_returns_fresh_banner(live_server: str) -> None:
    """GET /api/banners returns the new-labeled-pages banner for our fixture export."""
    import requests

    resp = requests.get(f"{live_server}/api/banners", timeout=5)
    assert resp.status_code == 200
    banners = resp.json()["banners"]
    ids = [b["id"] for b in banners]
    assert "new-labeled-pages" in ids, f"expected new-labeled-pages in {ids}"


@pytest.mark.e2e
@pytest.mark.filterwarnings("ignore::DeprecationWarning:websockets")
@pytest.mark.filterwarnings("ignore::DeprecationWarning:uvicorn")
def test_kanban_api_returns_fresh_row(live_server: str) -> None:
    """GET /api/profiles/all/datasets/recognition/kanban returns is_fresh=true for myproj."""
    import requests

    resp = requests.get(
        f"{live_server}/api/profiles/all/datasets/recognition/kanban",
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
def test_datasets_subpath_renders(page, live_server: str) -> None:
    """React Router sub-path /datasets/all/recognition serves the SPA index."""
    page.goto(f"{live_server}/datasets/all/recognition")
    page.wait_for_selector('[data-testid="home-page"]', timeout=5000)
    assert page.url.endswith("/datasets/all/recognition")
