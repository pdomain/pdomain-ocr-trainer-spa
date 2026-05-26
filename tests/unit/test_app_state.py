"""AppState wiring tests — build_app populates the adapter bundle."""

from __future__ import annotations

from pdomain_ocr_ops.gpu.protocols import LongJobRunner

from pdomain_ocr_trainer_spa.adapters.auth import IAuth
from pdomain_ocr_trainer_spa.adapters.dataset_sources import IDatasetSource
from pdomain_ocr_trainer_spa.adapters.model_registry import IModelRegistry
from pdomain_ocr_trainer_spa.adapters.storage import IStorage
from pdomain_ocr_trainer_spa.core.app_state import AppState


def test_build_app_populates_app_state(app) -> None:
    state = app.state.app_state
    assert isinstance(state, AppState)
    assert isinstance(state.storage, IStorage)
    assert isinstance(state.auth, IAuth)
    assert isinstance(state.model_registry, IModelRegistry)
    assert isinstance(state.job_runner, LongJobRunner)


def test_dataset_sources_include_local(app) -> None:
    sources = app.state.app_state.dataset_sources
    assert all(isinstance(s, IDatasetSource) for s in sources)
    assert any(s.name == "local" for s in sources)


def test_hydrate_from_disk_is_callable(settings) -> None:
    from pdomain_ocr_trainer_spa.bootstrap import _build_app_state

    state = _build_app_state(settings)
    state.hydrate_from_disk()  # idempotent no-op in M1
    assert state.profiles == {}
    assert state.runs == {}
