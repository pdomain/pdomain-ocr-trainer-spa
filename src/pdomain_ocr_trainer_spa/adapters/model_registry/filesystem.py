"""Filesystem-backed IModelRegistry — manages <shared-models>/<profile>/<task>/.

Models are discovered by scanning for ``*.metadata.json`` sidecar files; the
sidecar's directory is the model directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pdomain_ocr_trainer_spa.core.enums import TaskEnum
from pdomain_ocr_trainer_spa.core.errors import AdapterNotImplementedError
from pdomain_ocr_trainer_spa.core.models import (
    ModelPaths,
    ModelPublication,
    ModelSidecar,
    TrainedModel,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from pdomain_ops.gpu.types import JobEvent


class FilesystemModelRegistry:
    """The v1 IModelRegistry — trained models live under shared_models_dir."""

    def __init__(self, shared_models_dir: Path) -> None:
        self._root = Path(shared_models_dir)

    def _trained_model_from_sidecar(self, sidecar_path: Path) -> TrainedModel:
        sidecar = ModelSidecar.model_validate_json(sidecar_path.read_text())
        model_dir = sidecar_path.parent
        weights = next(
            (p for p in sorted(model_dir.iterdir()) if p.suffix in {".pt", ".safetensors"}),
            model_dir / f"{sidecar.name}.pt",
        )
        rel = model_dir.relative_to(self._root) if self._root in model_dir.parents else model_dir
        parts = rel.parts
        profile = parts[0] if parts else sidecar.name
        return TrainedModel(
            name=sidecar.name,
            profile=profile,
            task=TaskEnum(sidecar.task),
            language=sidecar.language or None,
            typeface=sidecar.typeface or None,
            paths=ModelPaths(weights=str(weights), sidecar=str(sidecar_path)),
            sidecar=sidecar,
        )

    def list(self) -> list[TrainedModel]:
        """Discover every trained model under shared_models_dir."""
        if not self._root.exists():
            return []
        return [
            self._trained_model_from_sidecar(sidecar_path)
            for sidecar_path in sorted(self._root.rglob("*.metadata.json"))
        ]

    def get(self, name: str) -> TrainedModel | None:
        """Return the trained model named ``name``, or None."""
        return next((m for m in self.list() if m.name == name), None)

    def write_artefacts(
        self,
        run: object,
        paths: ModelPaths,
        sidecar: ModelSidecar,
    ) -> TrainedModel:
        """Write the model weights + sidecar under shared_models_dir."""
        profile = str(getattr(run, "profile", sidecar.name))
        task = TaskEnum(sidecar.task)
        model_dir = self._root / profile / task.value / sidecar.name
        model_dir.mkdir(parents=True, exist_ok=True)
        sidecar_path = model_dir / f"{sidecar.name}.metadata.json"
        sidecar_path.write_text(sidecar.model_dump_json(indent=2))
        weights_dest = model_dir / Path(paths.weights).name
        src_weights = Path(paths.weights)
        if src_weights.exists() and src_weights != weights_dest:
            weights_dest.write_bytes(src_weights.read_bytes())
        return TrainedModel(
            name=sidecar.name,
            profile=profile,
            task=task,
            language=sidecar.language or None,
            typeface=sidecar.typeface or None,
            paths=ModelPaths(weights=str(weights_dest), sidecar=str(sidecar_path)),
            sidecar=sidecar,
        )

    def publish(
        self,
        model: TrainedModel,
        repo: str,
        on_event: Callable[[JobEvent], None],
    ) -> ModelPublication:
        """Filesystem registry cannot publish to a remote hub."""
        del model, repo, on_event
        raise AdapterNotImplementedError("Publishing from the filesystem model registry")
