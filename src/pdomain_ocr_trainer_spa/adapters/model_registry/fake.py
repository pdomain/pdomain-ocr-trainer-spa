"""FakeModelRegistry — in-memory IModelRegistry for tests (spec 14-testing §2.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pdomain_ocr_trainer_spa.core.enums import TaskEnum
from pdomain_ocr_trainer_spa.core.models import (
    ModelPaths,
    ModelPublication,
    ModelSidecar,
    TrainedModel,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from pdomain_ops.gpu.types import JobEvent


class FakeModelRegistry:
    """In-memory IModelRegistry — no filesystem, no remote hub."""

    def __init__(self) -> None:
        self._models: dict[str, TrainedModel] = {}

    def list(self) -> list[TrainedModel]:
        """Return all stored models, sorted by name."""
        return sorted(self._models.values(), key=lambda m: m.name)

    def get(self, name: str) -> TrainedModel | None:
        """Return the stored model named ``name``, or None."""
        return self._models.get(name)

    def write_artefacts(
        self,
        run: object,
        paths: ModelPaths,
        sidecar: ModelSidecar,
    ) -> TrainedModel:
        """Store a TrainedModel built from the run, paths and sidecar."""
        model = TrainedModel(
            name=sidecar.name,
            profile=str(getattr(run, "profile", sidecar.name)),
            task=TaskEnum(sidecar.task),
            language=sidecar.language or None,
            typeface=sidecar.typeface or None,
            paths=paths,
            sidecar=sidecar,
        )
        self._models[model.name] = model
        return model

    def publish(
        self,
        model: TrainedModel,
        repo: str,
        on_event: Callable[[JobEvent], None],
    ) -> ModelPublication:
        """Record a publication for the model and return it."""
        del on_event
        publication = ModelPublication(
            repo=repo,
            url=f"https://huggingface.co/{repo}",
            published_at=datetime.now(UTC),
        )
        stored = model.model_copy(update={"published_to": [*model.published_to, publication]})
        self._models[model.name] = stored
        return publication
