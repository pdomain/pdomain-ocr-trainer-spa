"""Browser/server verification for M12 typeface-classifier round-trip.

Exercises: kanban API returns 200 with typeface task, run form accepts
typeface-classification, React Router sub-path serves the SPA.

API tests use FastAPI TestClient (no real server required). Playwright
tests require ``make e2e-browser`` with a built frontend and are marked
``e2e`` to be excluded from ``make test``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from pdomain_ocr_trainer_spa.bootstrap import build_app
from pdomain_ocr_trainer_spa.core.enums import TypefaceEnum
from pdomain_ocr_trainer_spa.domain.profiles import create_profile
from pdomain_ocr_trainer_spa.settings import Settings

if TYPE_CHECKING:
    pass


@pytest.fixture(scope="module")
def typeface_settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    """Settings with a seeded typeface profile."""
    tmp = tmp_path_factory.mktemp("m12")
    s = Settings(
        app_data_root=tmp / "app",  # type: ignore[arg-type]
        ml_training_dir=tmp / "train",  # type: ignore[arg-type]
        ml_validation_dir=tmp / "val",  # type: ignore[arg-type]
        matched_ocr_dir=tmp / "matched-ocr",  # type: ignore[arg-type]
        shared_models_dir=tmp / "shared-models",  # type: ignore[arg-type]
        runs_dir=tmp / "runs",  # type: ignore[arg-type]
        jobs_db_path=tmp / "jobs.db",  # type: ignore[arg-type]
        job_runner_kind="fake",
        model_registry_kind="fake",
        host="127.0.0.1",
        port=8092,
        enable_typeface_training=True,
    )
    # Seed profile + typeface training data
    # Directory name must match TaskEnum.typeface_classification.value = "typeface-classification"
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


@pytest.fixture(scope="module")
def typeface_client(typeface_settings: Settings) -> TestClient:
    """TestClient backed by the typeface-seeded settings."""
    # Ensure static/ has at minimum an index.html so the catch-all works.
    static_dir = Path(__file__).resolve().parents[2] / "src" / "pdomain_ocr_trainer_spa" / "static"
    static_dir.mkdir(exist_ok=True)
    index_html = static_dir / "index.html"
    if not index_html.exists():
        index_html.write_text(
            '<html><body data-testid="home-page">OCR Trainer M12</body></html>',
            encoding="utf-8",
        )
    app = build_app(typeface_settings)
    return TestClient(app, raise_server_exceptions=True)


@pytest.mark.e2e
def test_typeface_kanban_api_returns_200(typeface_client: TestClient) -> None:
    """GET .../datasets/typeface-classification/kanban → 200 with kanban view."""
    resp = typeface_client.get(
        "/api/profiles/testprofile/datasets/typeface-classification/kanban",
    )
    assert resp.status_code == 200, resp.text
    view = resp.json()
    assert view["task"] == "typeface-classification"
    assert "columns" in view


@pytest.mark.e2e
def test_run_form_accepts_typeface_classification(typeface_client: TestClient) -> None:
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
def test_spa_root_serves_html(typeface_client: TestClient) -> None:
    """GET / serves the SPA index.html (catch-all active)."""
    resp = typeface_client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.e2e
def test_spa_typeface_subpath_serves_html(typeface_client: TestClient) -> None:
    """GET /profiles/testprofile/datasets/typeface-classification serves HTML.

    The React Router sub-path is handled by the SPA catch-all.
    """
    resp = typeface_client.get(
        "/profiles/testprofile/datasets/typeface-classification",
    )
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.e2e
def test_typeface_kanban_columns_present(typeface_client: TestClient) -> None:
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


# ---------------------------------------------------------------------------
# Playwright smoke tests — only run when a real built frontend is available
# via ``make e2e-browser`` (requires --base-url).
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_home_page_loads(page, base_url: str) -> None:  # type: ignore[no-untyped-def]
    """SPA serves the shell on ``/`` with no console errors.

    Requires a real running server (``--base-url``); skipped when
    ``--base-url`` is not set (pure-CI mode without a live server).
    """
    if not base_url:
        pytest.skip("--base-url not provided; skip live-server Playwright test")
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(base_url)
    # With a real frontend, the AppShell will render; with a minimal
    # fake index.html we just check for a page-level element.
    page.wait_for_load_state("domcontentloaded", timeout=8000)
    assert not errors, f"Console errors on /: {errors}"
