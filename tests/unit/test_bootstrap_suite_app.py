"""Tests for `bootstrap._build_suite_app()` / `_migrate_unknown_app_prefs()`.

Without a `suite_app=`, `mount_routes()` mounts `/api/suite/device` and
`/healthz` under `app_id="unknown"` -- any compute-device preference a user
set landed in `apps["unknown"]` instead of the real app's section. Locks in:
  - `_build_suite_app()` reads the bundled `pdomain-suite.json` fragment and
    returns an `InstalledApp` with the real `app_id`, `sys.executable` as
    `binary`, and the installed package version.
  - `_migrate_unknown_app_prefs()` copies a stray `compute_device` from
    `apps["unknown"]` to the real app_id's section (when the real section
    doesn't already have one) and clears it from "unknown".
  - `build_app()` mounts suite routes under the real app_id end to end.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from pdomain_ops.suite.prefs import LocalFilePrefs

from pdomain_ocr_trainer_spa.bootstrap import (
    _build_suite_app,
    _migrate_unknown_app_prefs,
    build_app,
)
from pdomain_ocr_trainer_spa.settings import Settings

if TYPE_CHECKING:
    from pathlib import Path

_APP_ID = "pdomain-ocr-trainer-spa"


@pytest.fixture
def suite_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient wired to a tmp_path-isolated suite prefs file."""
    monkeypatch.setenv("PD_SUITE_DATA_DIR", str(tmp_path / "suite_data"))
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
    return TestClient(build_app(settings))


def test_build_suite_app_uses_real_app_id_and_this_interpreter() -> None:
    suite_app = _build_suite_app()
    assert suite_app.app_id == _APP_ID
    assert suite_app.package == _APP_ID
    assert suite_app.binary == sys.executable
    assert suite_app.version  # non-empty; exact value depends on install


def test_migrate_moves_stray_compute_device_to_real_app_id(tmp_path: Path) -> None:
    prefs = LocalFilePrefs(root=tmp_path / "ui-prefs.json")
    prefs.write_app("unknown", {"compute_device": "cuda"})

    _migrate_unknown_app_prefs(prefs, _APP_ID)

    snapshot = prefs.read()
    assert snapshot.apps[_APP_ID]["compute_device"] == "cuda"
    assert "compute_device" not in snapshot.apps["unknown"]


def test_migrate_does_not_clobber_existing_real_app_value(tmp_path: Path) -> None:
    prefs = LocalFilePrefs(root=tmp_path / "ui-prefs.json")
    prefs.write_app("unknown", {"compute_device": "cuda"})
    prefs.write_app(_APP_ID, {"compute_device": "mps"})

    _migrate_unknown_app_prefs(prefs, _APP_ID)

    snapshot = prefs.read()
    assert snapshot.apps[_APP_ID]["compute_device"] == "mps"
    assert snapshot.apps["unknown"]["compute_device"] == "cuda"


def test_healthz_reports_real_app_id(suite_client: TestClient) -> None:
    resp = suite_client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["app_id"] == _APP_ID


def test_put_device_persists_under_real_app_id(suite_client: TestClient, tmp_path: Path) -> None:
    resp = suite_client.put("/api/suite/device", json={"scope": "app", "device": "cpu"})
    assert resp.status_code == 200

    prefs = LocalFilePrefs(root=tmp_path / "suite_data" / "ui-prefs.json")
    snapshot = prefs.read()
    assert snapshot.apps[_APP_ID]["compute_device"] == "cpu"
    assert "unknown" not in snapshot.apps
