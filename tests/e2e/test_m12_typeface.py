"""M12 typeface-classifier end-to-end verification.

Two test tiers:
  1. API tests (no browser) — TestClient + ``@pytest.mark.e2e``.
     These run whenever a browser is not available and verify the backend
     round-trips.  They are the fallback for pure-CI environments where
     Playwright is not installed.

  2. Browser tests (Playwright, live uvicorn) — ``@pytest.mark.e2e`` +
     ``@pytest.mark.filterwarnings`` per the sibling worktree pattern from
     ``tests/e2e/test_labeler_freshness.py``.  They start a real uvicorn
     server on port 8092 with a seeded typeface profile and fake index.html,
     then drive headless Chromium against it.

Run with::

    make e2e-browser      # browser tier runs (requires playwright-install)
    uv run pytest tests/e2e/ -m e2e --no-cov  # both tiers
"""

from __future__ import annotations

import json
import socket
import threading
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from pdomain_ocr_trainer_spa.bootstrap import build_app
from pdomain_ocr_trainer_spa.core.enums import TypefaceEnum
from pdomain_ocr_trainer_spa.domain.profiles import create_profile
from pdomain_ocr_trainer_spa.settings import Settings

_E2E_PORT = 8092
_STATIC_DIR = Path(__file__).resolve().parents[2] / "src" / "pdomain_ocr_trainer_spa" / "static"
_FAKE_INDEX = '<html><body data-testid="home-page">OCR Trainer M12</body></html>'


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _wait_for_port(host: str, port: int, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Server on {host}:{port} did not start within {timeout}s")


def _make_settings(tmp: Path) -> Settings:
    s = Settings(
        app_data_root=tmp / "app",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        ml_training_dir=tmp / "train",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        ml_validation_dir=tmp / "val",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        matched_ocr_dir=tmp / "matched-ocr",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        shared_models_dir=tmp / "shared-models",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        runs_dir=tmp / "runs",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        jobs_db_path=tmp / "jobs.db",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        job_runner_kind="fake",
        model_registry_kind="fake",
        host="127.0.0.1",
        port=_E2E_PORT,
        enable_typeface_training=True,
    )
    # Seed profile + typeface training data.
    # Directory name = TaskEnum.typeface_classification.value = "typeface-classification"
    create_profile(s, name="testprofile", language="en", typeface=TypefaceEnum.roman)
    tc_dir = s.ml_training_dir / "testprofile" / "typeface-classification"
    tc_dir.mkdir(parents=True)
    (tc_dir / "metadata.jsonl").write_text(
        json.dumps({"file_name": "c001.png", "typeface": "roman"}) + "\n",
        encoding="utf-8",
    )
    (tc_dir / "images").mkdir()
    (tc_dir / "images" / "c001.png").write_bytes(b"\x89PNG")
    return s


# ---------------------------------------------------------------------------
# Module-scoped TestClient fixture (no browser required)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def typeface_settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    return _make_settings(tmp_path_factory.mktemp("m12-api"))


@pytest.fixture(scope="module")
def typeface_client(typeface_settings: Settings):  # type: ignore[no-untyped-def]  # pytest fixture return is supplied by TestClient
    """FastAPI TestClient backed by the typeface-seeded settings."""
    from fastapi.testclient import TestClient

    _STATIC_DIR.mkdir(exist_ok=True)
    index_html = _STATIC_DIR / "index.html"
    if not index_html.exists():
        index_html.write_text(_FAKE_INDEX, encoding="utf-8")
    app = build_app(typeface_settings)
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Module-scoped live-server fixture (browser tier)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def live_server(tmp_path_factory: pytest.TempPathFactory) -> Generator[str]:
    """Start the real FastAPI app on port 8092; yield the base URL."""
    import uvicorn

    s = _make_settings(tmp_path_factory.mktemp("m12-browser"))
    _STATIC_DIR.mkdir(exist_ok=True)
    (_STATIC_DIR / "index.html").write_text(_FAKE_INDEX, encoding="utf-8")
    app = build_app(s)
    config = uvicorn.Config(app, host="127.0.0.1", port=_E2E_PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_for_port("127.0.0.1", _E2E_PORT)
    yield f"http://127.0.0.1:{_E2E_PORT}"
    server.should_exit = True


# ---------------------------------------------------------------------------
# Tier 1: API tests (TestClient, no browser)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_typeface_kanban_api_returns_200(typeface_client) -> None:  # type: ignore[no-untyped-def]  # pytest injects an untyped fixture
    """GET .../datasets/typeface-classification/kanban → 200 with kanban view."""
    resp = typeface_client.get(
        "/api/profiles/testprofile/datasets/typeface-classification/kanban",
    )
    assert resp.status_code == 200, resp.text
    view = resp.json()
    assert view["task"] == "typeface-classification"
    assert "columns" in view


@pytest.mark.e2e
def test_typeface_kanban_columns_present(typeface_client) -> None:  # type: ignore[no-untyped-def]  # pytest injects an untyped fixture
    """Kanban view has unassigned, train, val columns with the seeded crop."""
    resp = typeface_client.get(
        "/api/profiles/testprofile/datasets/typeface-classification/kanban",
    )
    assert resp.status_code == 200, resp.text
    view = resp.json()
    columns = view["columns"]
    assert set(columns.keys()) == {"unassigned", "train", "val"}
    all_rows = [r for col in columns.values() for r in col["rows"]]
    assert len(all_rows) >= 1, "Expected at least 1 row from the seeded metadata.jsonl"


@pytest.mark.e2e
def test_run_form_accepts_typeface_classification(typeface_client) -> None:  # type: ignore[no-untyped-def]  # pytest injects an untyped fixture
    """POST /api/runs with task=typeface-classification → 202."""
    resp = typeface_client.post(
        "/api/runs",
        json={
            "profile": "testprofile",
            "task": "typeface-classification",
            "args": {},
        },
    )
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "run_id" in data


@pytest.mark.e2e
def test_spa_root_serves_html(typeface_client) -> None:  # type: ignore[no-untyped-def]  # pytest injects an untyped fixture
    """GET / serves the SPA index.html (catch-all active)."""
    resp = typeface_client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.e2e
def test_spa_typeface_subpath_serves_html(typeface_client) -> None:  # type: ignore[no-untyped-def]  # pytest injects an untyped fixture
    """GET /profiles/testprofile/datasets/typeface-classification serves HTML.

    The React Router sub-path is handled by the SPA catch-all.
    """
    resp = typeface_client.get(
        "/profiles/testprofile/datasets/typeface-classification",
    )
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Tier 2: Browser tests (Playwright + live uvicorn server)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@pytest.mark.filterwarnings("ignore::DeprecationWarning:websockets")
@pytest.mark.filterwarnings("ignore::DeprecationWarning:uvicorn")
def test_browser_home_page_loads(page, live_server: str) -> None:  # type: ignore[no-untyped-def]  # Playwright page fixture is untyped
    """SPA index.html is served; Playwright can reach the fake home-page testid."""
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(live_server)
    page.wait_for_selector('[data-testid="home-page"]', timeout=5000)
    assert not errors, f"console errors on /: {errors}"


@pytest.mark.e2e
@pytest.mark.filterwarnings("ignore::DeprecationWarning:websockets")
@pytest.mark.filterwarnings("ignore::DeprecationWarning:uvicorn")
def test_browser_typeface_kanban_api(live_server: str) -> None:  # type: ignore[no-untyped-def]  # pytest fixture typing is external to this test
    """GET /api/profiles/testprofile/datasets/typeface-classification/kanban
    returns 200 from a real uvicorn server."""
    import requests

    resp = requests.get(
        f"{live_server}/api/profiles/testprofile/datasets/typeface-classification/kanban",
        timeout=5,
    )
    assert resp.status_code == 200
    view = resp.json()
    assert view["task"] == "typeface-classification"


@pytest.mark.e2e
@pytest.mark.filterwarnings("ignore::DeprecationWarning:websockets")
@pytest.mark.filterwarnings("ignore::DeprecationWarning:uvicorn")
def test_browser_run_creation(live_server: str) -> None:  # type: ignore[no-untyped-def]  # pytest fixture typing is external to this test
    """POST /api/runs with typeface-classification returns 202 from a real
    uvicorn server."""
    import requests

    resp = requests.post(
        f"{live_server}/api/runs",
        json={
            "profile": "testprofile",
            "task": "typeface-classification",
            "args": {},
        },
        timeout=5,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "run_id" in data


@pytest.mark.e2e
@pytest.mark.filterwarnings("ignore::DeprecationWarning:websockets")
@pytest.mark.filterwarnings("ignore::DeprecationWarning:uvicorn")
def test_browser_typeface_subpath_direct_load(page, live_server: str) -> None:  # type: ignore[no-untyped-def]  # Playwright page fixture is untyped
    """React Router sub-path /profiles/testprofile/datasets/typeface-classification
    renders via the SPA catch-all when loaded directly in a browser."""
    page.goto(f"{live_server}/profiles/testprofile/datasets/typeface-classification")
    page.wait_for_selector('[data-testid="home-page"]', timeout=5000)
    assert "typeface-classification" in page.url
