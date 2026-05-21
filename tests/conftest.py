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


@pytest.fixture
def fake_runner(app):
    """The app's wired-in FakeLongJobRunner (Settings.job_runner_kind='fake')."""
    return app.state.app_state.job_runner


@pytest.fixture
def trained_profile(settings: Settings):
    """Create a complete profile with recognition + detection training data.

    Returns the profile name; the profile has a language + typeface (so model
    names derive cleanly) and one ``labels.json`` entry per supported task.
    """
    import json

    from pd_ocr_trainer_spa.core.enums import TypefaceEnum
    from pd_ocr_trainer_spa.domain.profiles import create_profile

    create_profile(
        settings,
        name="clogaelach",
        language="ga",
        typeface=TypefaceEnum.clogaelach,
    )
    for task, value in (
        ("recognition", "an focal"),
        ("detection", {"polygons": [[[0, 0], [1, 0], [1, 1], [0, 1]]]}),
    ):
        task_dir = settings.ml_training_dir / "clogaelach" / task
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "labels.json").write_text(
            json.dumps({"item-1": value}), encoding="utf-8"
        )
    return "clogaelach"
