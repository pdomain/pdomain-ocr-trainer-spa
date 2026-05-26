"""IDatasetSource Protocol + row-ref models (spec 02-backend §4.4)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel

from pdomain_ocr_trainer_spa.core.enums import SplitEnum, TaskEnum

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class DatasetPageRef(BaseModel):
    """A detection-task page row from a dataset source."""

    project_id: str
    page_name: str
    width: int
    height: int
    label_bbox_count: int
    in_split: SplitEnum
    style_tags: list[str] = []


class DatasetCropRef(BaseModel):
    """A recognition-task crop row from a dataset source."""

    project_id: str
    crop_name: str
    page_name: str
    label_text: str
    style_tags: list[str] = []


@runtime_checkable
class IDatasetSource(Protocol):
    """A source of dataset rows (local export root, or a remote dataset hub)."""

    name: str

    def list(
        self,
        profile: str,
        task: TaskEnum,
        split: SplitEnum,
    ) -> Iterator[DatasetPageRef | DatasetCropRef]: ...

    def fetch_to_local(self, profile: str, task: TaskEnum, split: SplitEnum) -> Path: ...
