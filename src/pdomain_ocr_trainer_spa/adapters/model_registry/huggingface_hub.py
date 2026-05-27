"""HuggingFace Hub IModelRegistry — deferred post-core-parity (D-T2).

This module imports clean; every method raises AdapterNotImplementedError on call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pdomain_ocr_trainer_spa.core.errors import AdapterNotImplementedError

if TYPE_CHECKING:
    from collections.abc import Callable

    from pdomain_ops.gpu.types import JobEvent

    from pdomain_ocr_trainer_spa.core.models import (
        ModelPaths,
        ModelPublication,
        ModelSidecar,
        TrainedModel,
    )


class HuggingFaceHubModelRegistry:
    """Deferred HF Hub model registry — constructs, but every method raises."""

    def list(self) -> list[TrainedModel]:
        """Deferred — raises AdapterNotImplementedError."""
        raise AdapterNotImplementedError("HuggingFace Hub model registry")

    def get(self, name: str) -> TrainedModel | None:
        """Deferred — raises AdapterNotImplementedError."""
        raise AdapterNotImplementedError("HuggingFace Hub model registry")

    def write_artefacts(
        self,
        run: object,
        paths: ModelPaths,
        sidecar: ModelSidecar,
    ) -> TrainedModel:
        """Deferred — raises AdapterNotImplementedError."""
        raise AdapterNotImplementedError("HuggingFace Hub model registry")

    def publish(
        self,
        model: TrainedModel,
        repo: str,
        on_event: Callable[[JobEvent], None],
    ) -> ModelPublication:
        """Deferred — raises AdapterNotImplementedError."""
        raise AdapterNotImplementedError("HuggingFace Hub model registry")
