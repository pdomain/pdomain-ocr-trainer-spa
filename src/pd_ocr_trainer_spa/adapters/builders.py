"""Construct adapter implementations from Settings (spec 02-backend §3)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pd_ocr_trainer_spa.adapters.auth.none_ import NoneAuth
from pd_ocr_trainer_spa.adapters.dataset_sources.local import LocalDatasetSource
from pd_ocr_trainer_spa.adapters.model_registry.filesystem import FilesystemModelRegistry
from pd_ocr_trainer_spa.adapters.model_registry.huggingface_hub import (
    HuggingFaceHubModelRegistry,
)
from pd_ocr_trainer_spa.adapters.storage.filesystem import FilesystemStorage
from pd_ocr_trainer_spa.adapters.storage.s3 import S3Storage

if TYPE_CHECKING:
    from pd_ocr_ops.gpu.protocols import LongJobRunner

    from pd_ocr_trainer_spa.adapters.auth import IAuth
    from pd_ocr_trainer_spa.adapters.dataset_sources import IDatasetSource
    from pd_ocr_trainer_spa.adapters.model_registry import IModelRegistry
    from pd_ocr_trainer_spa.adapters.storage import IStorage
    from pd_ocr_trainer_spa.settings import Settings


def build_storage(settings: Settings) -> IStorage:
    """Return the IStorage impl selected by ``settings.storage_kind``."""
    if settings.storage_kind == "s3":
        return S3Storage()
    return FilesystemStorage()


def build_auth(settings: Settings) -> IAuth:
    """Return the IAuth impl selected by ``settings.auth_kind``."""
    del settings  # only "none" exists in v1
    return NoneAuth()


def build_dataset_sources(settings: Settings) -> list[IDatasetSource]:
    """Return the configured dataset sources (local is always present)."""
    return [
        LocalDatasetSource(
            ml_training_dir=settings.ml_training_dir,
            ml_validation_dir=settings.ml_validation_dir,
        )
    ]


def build_model_registry(settings: Settings) -> IModelRegistry:
    """Return the IModelRegistry impl selected by ``settings.model_registry_kind``."""
    if settings.model_registry_kind == "huggingface_hub":
        return HuggingFaceHubModelRegistry()
    if settings.model_registry_kind == "fake":
        from pd_ocr_trainer_spa.adapters.model_registry.fake import FakeModelRegistry

        return FakeModelRegistry()
    return FilesystemModelRegistry(shared_models_dir=settings.shared_models_dir)


def build_job_runner(settings: Settings) -> LongJobRunner:
    """Return the pd-ocr-ops LongJobRunner selected by ``settings.job_runner_kind``.

    The pd-ocr-ops LongJobRunner Protocol declares ``stream_events`` as an
    async method returning an AsyncIterator; every concrete impl (including
    pd-ocr-ops' own LocalLongJobRunner) implements it as an async generator,
    which basedpyright sees as a structural mismatch. The ignores below track
    that upstream Protocol-shape quirk — see docs/conventions/lint-deviations.md.
    """
    if settings.job_runner_kind == "fake":
        from pd_ocr_trainer_spa.training.fake_runner import FakeLongJobRunner

        return FakeLongJobRunner()  # pyright: ignore[reportReturnType]
    from pd_ocr_ops.gpu.local_jobs import LocalLongJobRunner

    return LocalLongJobRunner(  # pyright: ignore[reportReturnType]
        db_path=settings.jobs_db_path,
    )
