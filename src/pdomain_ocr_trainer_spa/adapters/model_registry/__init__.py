"""IModelRegistry Protocol (spec 02-backend §4.5).

The ``write_artefacts`` ``run`` parameter is typed ``object`` until the full
``Run`` model lands in its own milestone; impls only read attributes off it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Callable

    from pdomain_ocr_ops.gpu.types import JobEvent

    from pdomain_ocr_trainer_spa.core.models import (
        ModelPaths,
        ModelPublication,
        ModelSidecar,
        TrainedModel,
    )


@runtime_checkable
class IModelRegistry(Protocol):
    """Trained-model storage + discovery + publish surface."""

    def list(self) -> list[TrainedModel]: ...

    def get(self, name: str) -> TrainedModel | None: ...

    def write_artefacts(
        self,
        run: object,
        paths: ModelPaths,
        sidecar: ModelSidecar,
    ) -> TrainedModel: ...

    def publish(
        self,
        model: TrainedModel,
        repo: str,
        on_event: Callable[[JobEvent], None],
    ) -> ModelPublication: ...
