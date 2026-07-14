"""Tests for GET/PATCH /api/ui-prefs — UIPrefsConfig persistence endpoint."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from pdomain_ocr_trainer_spa.bootstrap import build_app
    from pdomain_ocr_trainer_spa.settings import Settings

    settings = Settings(
        ml_training_dir=tmp_path / "ml-training",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        ml_validation_dir=tmp_path / "ml-validation",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        matched_ocr_dir=tmp_path / "matched-ocr",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        app_data_root=tmp_path / "app-data",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        shared_models_dir=tmp_path / "shared-models",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        runs_dir=tmp_path / "app-data" / "runs",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        jobs_db_path=tmp_path / "app-data" / "jobs.db",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        job_runner_kind="fake",
        model_registry_kind="fake",
    )
    app = build_app(settings)
    return TestClient(app)


def test_get_ui_prefs_default(client):
    """First launch returns 200 with defaults, not 404."""
    resp = client.get("/api/ui-prefs")
    assert resp.status_code == 200
    data = resp.json()
    assert "theme" in data
    assert data["theme"] in ("dark", "light")


def test_patch_ui_prefs_persists(client):
    """PATCH round-trips; subsequent GET returns updated value."""
    patch_resp = client.patch(
        "/api/ui-prefs",
        json={"theme": "light"},
    )
    assert patch_resp.status_code == 200
    get_resp = client.get("/api/ui-prefs")
    assert get_resp.json()["theme"] == "light"
