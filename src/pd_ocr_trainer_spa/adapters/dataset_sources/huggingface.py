"""HuggingFace IDatasetSource — deferred post-core-parity (D-T2).

This module imports clean; every method raises AdapterNotImplementedError on call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pd_ocr_trainer_spa.core.errors import AdapterNotImplementedError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from pd_ocr_trainer_spa.adapters.dataset_sources import DatasetCropRef, DatasetPageRef
    from pd_ocr_trainer_spa.core.enums import SplitEnum, TaskEnum


class HuggingFaceDatasetSource:
    """Deferred HF dataset source — constructs, but every method raises."""

    name = "huggingface"

    def list(
        self,
        profile: str,
        task: TaskEnum,
        split: SplitEnum,
    ) -> Iterator[DatasetPageRef | DatasetCropRef]:
        """Deferred — raises AdapterNotImplementedError."""
        raise AdapterNotImplementedError("HuggingFace dataset source")

    def fetch_to_local(self, profile: str, task: TaskEnum, split: SplitEnum) -> Path:
        """Deferred — raises AdapterNotImplementedError."""
        raise AdapterNotImplementedError("HuggingFace dataset source")
