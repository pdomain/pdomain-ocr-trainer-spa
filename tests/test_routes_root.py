"""SPA-serving contract tests.

Workspace-mandated tests (per CLAUDE.md + specs/14-testing.md §6):
  1. GET / → 200 text/html
  2. React-Router sub-paths → 200 HTML (catch-all falls through to index.html)
  3. /api/* routes are NOT shadowed by the catch-all
  4. GET / → 503 when the frontend directory is absent

Tests use monkeypatch + tmp_path so they run without a real frontend
build and NEVER skip.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import pd_ocr_trainer_spa.bootstrap as bootstrap_module
from pd_ocr_trainer_spa.bootstrap import build_app
from pd_ocr_trainer_spa.settings import Settings


@pytest.fixture
def base_settings(tmp_path: pytest.TempPathFactory) -> Settings:
    return Settings(
        ml_training_dir=tmp_path / "ml-training",  # type: ignore[arg-type]
        ml_validation_dir=tmp_path / "ml-validation",  # type: ignore[arg-type]
        matched_ocr_dir=tmp_path / "matched-ocr",  # type: ignore[arg-type]
        app_data_root=tmp_path / "app-data",  # type: ignore[arg-type]
        shared_models_dir=tmp_path / "shared-models",  # type: ignore[arg-type]
        runs_dir=tmp_path / "app-data" / "runs",  # type: ignore[arg-type]
        jobs_db_path=tmp_path / "app-data" / "jobs.db",  # type: ignore[arg-type]
        labeler_export_root=None,
        job_runner_kind="fake",
        model_registry_kind="fake",
    )


@pytest.fixture
def app_with_frontend(tmp_path, monkeypatch, base_settings):
    """App with a minimal fake frontend build in place."""
    # Create minimal fake SPA build
    static_dir = tmp_path / "fake-static"
    (static_dir / "assets").mkdir(parents=True)
    (static_dir / "index.html").write_text(
        "<!DOCTYPE html><html><body>pd-ocr-trainer-spa SPA</body></html>"
    )
    (static_dir / "assets" / "index.js").write_text("// fake asset")

    # Patch _STATIC_DIR in the bootstrap module so the app reads from fake static
    monkeypatch.setattr(bootstrap_module, "_STATIC_DIR", static_dir)

    return TestClient(build_app(base_settings))


def test_root_returns_html(app_with_frontend: TestClient) -> None:
    """GET / → 200 text/html with the SPA index.html content."""
    resp = app_with_frontend.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<!DOCTYPE html>" in resp.text


def test_spa_react_router_paths_return_html(app_with_frontend: TestClient) -> None:
    """React-Router sub-paths are served the SPA index.html (200 HTML)."""
    for path in ["/runs/123", "/profiles/all", "/models", "/runs"]:
        resp = app_with_frontend.get(path)
        assert resp.status_code == 200, f"Expected 200 for {path}, got {resp.status_code}"
        assert "text/html" in resp.headers["content-type"]


def test_api_env_js_not_shadowed(app_with_frontend: TestClient) -> None:
    """/env.js must return JS, not HTML — the API route is not swallowed by the catch-all."""
    resp = app_with_frontend.get("/env.js")
    assert resp.status_code == 200
    assert "application/javascript" in resp.headers["content-type"]
    assert "__APP_ENV__" in resp.text


def test_api_env_js_exposes_driver_contract_version(
    app_with_frontend: TestClient,
) -> None:
    """/env.js exposes driverContractVersion (spec 13 §6, initial = 1)."""
    resp = app_with_frontend.get("/env.js")
    assert resp.status_code == 200
    assert '"driverContractVersion": 1' in resp.text


def test_root_503_when_frontend_absent(tmp_path, monkeypatch, base_settings) -> None:
    """GET / → 503 when the static directory has no index.html."""
    # Point to a nonexistent directory
    monkeypatch.setattr(bootstrap_module, "_STATIC_DIR", tmp_path / "nonexistent")

    client = TestClient(build_app(base_settings), raise_server_exceptions=False)
    resp = client.get("/")
    assert resp.status_code == 503
