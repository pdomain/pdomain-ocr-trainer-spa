"""Local-filesystem IDatasetSource — reads the on-disk DocTR dataset layout.

Layout (spec 01-data-models §2.1):
    <ml_dir>/<profile>/<task>/images/*.{png,jpg}
    <ml_dir>/<profile>/<task>/labels.json

A task folder counts as a dataset only when its labels.json exists.
``ExportManager`` (which materialises unassigned export rows and has
import-time filesystem side effects) is wired in a later dataset milestone;
the M1 adapter resolves rows from the train/val directories directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from pd_ocr_trainer_spa.adapters.dataset_sources import DatasetCropRef, DatasetPageRef
from pd_ocr_trainer_spa.core.enums import SplitEnum, TaskEnum

if TYPE_CHECKING:
    from collections.abc import Iterator


class LocalDatasetSource:
    """The v1 IDatasetSource — reads ml-training / ml-validation directories."""

    name = "local"

    def __init__(self, ml_training_dir: Path, ml_validation_dir: Path) -> None:
        self._train_dir = Path(ml_training_dir)
        self._val_dir = Path(ml_validation_dir)

    def _ml_dir_for(self, split: SplitEnum) -> Path | None:
        if split is SplitEnum.train:
            return self._train_dir
        if split is SplitEnum.val:
            return self._val_dir
        return None  # unassigned rows come from the export root (later milestone)

    def _task_dir(self, profile: str, task: TaskEnum, split: SplitEnum) -> Path | None:
        ml_dir = self._ml_dir_for(split)
        if ml_dir is None:
            return None
        task_dir = ml_dir / profile / task.value
        if not (task_dir / "labels.json").exists():
            return None
        return task_dir

    def list(
        self,
        profile: str,
        task: TaskEnum,
        split: SplitEnum,
    ) -> Iterator[DatasetPageRef | DatasetCropRef]:
        """Yield the dataset rows for one profile / task / split."""
        task_dir = self._task_dir(profile, task, split)
        if task_dir is None:
            return
        labels: dict[str, object] = json.loads((task_dir / "labels.json").read_text())
        for image_name, value in sorted(labels.items()):
            if task is TaskEnum.recognition:
                yield DatasetCropRef(
                    project_id=profile,
                    crop_name=image_name,
                    page_name=image_name,
                    label_text=str(value),
                )
            else:
                bbox_count = len(value) if isinstance(value, list) else 0
                yield DatasetPageRef(
                    project_id=profile,
                    page_name=image_name,
                    width=0,
                    height=0,
                    label_bbox_count=bbox_count,
                    in_split=split,
                )

    def fetch_to_local(self, profile: str, task: TaskEnum, split: SplitEnum) -> Path:
        """Return the local DocTR-compatible directory; local data is already on disk."""
        task_dir = self._task_dir(profile, task, split)
        if task_dir is None:
            ml_dir = self._ml_dir_for(split)
            base = ml_dir if ml_dir is not None else self._train_dir
            return base / profile / task.value
        return task_dir
