"""Shared pytest fixtures for pd-ocr-trainer-spa."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pd_ocr_trainer_spa.bootstrap import build_app
from pd_ocr_trainer_spa.settings import Settings


@pytest.fixture
def settings(tmp_path: pytest.TempPathFactory) -> Settings:
    """Minimal settings pointing everything at tmp_path."""
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
def app(settings: Settings):
    """FastAPI app configured with test settings."""
    return build_app(settings)


@pytest.fixture
def client(app):
    """TestClient for the FastAPI app."""
    return TestClient(app)
