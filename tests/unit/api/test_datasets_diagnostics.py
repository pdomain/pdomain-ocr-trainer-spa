"""Tests for GET /api/labeler-export-diagnostics endpoint (Track D)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from pdomain_ocr_trainer_spa.bootstrap import build_app
from pdomain_ocr_trainer_spa.settings import Settings


def test_diagnostics_configured(tmp_path: Path) -> None:
    export = tmp_path / "export"
    export.mkdir()
    s = Settings(
        labeler_export_root=export,  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        app_data_root=tmp_path / "app",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        runs_dir=tmp_path / "runs",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        jobs_db_path=tmp_path / "jobs.db",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
        job_runner_kind="fake",
        model_registry_kind="fake",
    )
    client = TestClient(build_app(s))
    resp = client.get("/api/labeler-export-diagnostics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "configured"
    assert data["export_root"] == str(export)


def test_diagnostics_absent(tmp_path: Path) -> None:
    with patch(
        "pdomain_ocr_trainer_spa.domain.labeler_export._shared_path_lookup",
        return_value=None,
    ):
        s = Settings(
            labeler_export_root=None,
            app_data_root=tmp_path / "app",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
            runs_dir=tmp_path / "runs",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
            jobs_db_path=tmp_path / "jobs.db",  # type: ignore[arg-type]  # Settings accepts Path values at runtime
            job_runner_kind="fake",
            model_registry_kind="fake",
        )
        client = TestClient(build_app(s))
        resp = client.get("/api/labeler-export-diagnostics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "absent"
    assert data["export_root"] is None
