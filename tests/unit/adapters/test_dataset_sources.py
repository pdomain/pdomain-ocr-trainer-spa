"""IDatasetSource adapter tests: LocalDatasetSource + HuggingFaceDatasetSource."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from pd_ocr_trainer_spa.adapters.dataset_sources import (
    DatasetCropRef,
    DatasetPageRef,
    IDatasetSource,
)
from pd_ocr_trainer_spa.adapters.dataset_sources.huggingface import HuggingFaceDatasetSource
from pd_ocr_trainer_spa.adapters.dataset_sources.local import LocalDatasetSource
from pd_ocr_trainer_spa.core.enums import SplitEnum, TaskEnum


def _write_dataset(ml_dir, profile: str, task: str, labels: dict[str, object]) -> None:
    task_dir = ml_dir / profile / task
    (task_dir / "images").mkdir(parents=True)
    (task_dir / "labels.json").write_text(json.dumps(labels))


def test_local_source_satisfies_protocol(tmp_path) -> None:
    src = LocalDatasetSource(tmp_path / "t", tmp_path / "v")
    assert isinstance(src, IDatasetSource)
    assert src.name == "local"


def test_local_source_lists_detection_pages(tmp_path) -> None:
    train = tmp_path / "t"
    _write_dataset(train, "all", "detection", {"p1.png": [{}, {}], "p2.png": [{}]})
    src = LocalDatasetSource(train, tmp_path / "v")
    rows = list(src.list("all", TaskEnum.detection, SplitEnum.train))
    assert all(isinstance(r, DatasetPageRef) for r in rows)
    assert {r.page_name: r.label_bbox_count for r in rows} == {"p1.png": 2, "p2.png": 1}  # type: ignore[union-attr]


def test_local_source_lists_recognition_crops(tmp_path) -> None:
    val = tmp_path / "v"
    _write_dataset(val, "all", "recognition", {"c1.png": "hello", "c2.png": "world"})
    src = LocalDatasetSource(tmp_path / "t", val)
    rows = list(src.list("all", TaskEnum.recognition, SplitEnum.val))
    assert all(isinstance(r, DatasetCropRef) for r in rows)
    assert {r.crop_name: r.label_text for r in rows} == {  # type: ignore[union-attr]
        "c1.png": "hello",
        "c2.png": "world",
    }


def test_local_source_missing_labels_yields_nothing(tmp_path) -> None:
    src = LocalDatasetSource(tmp_path / "t", tmp_path / "v")
    assert list(src.list("all", TaskEnum.detection, SplitEnum.train)) == []


def test_local_source_unassigned_split_yields_nothing(tmp_path) -> None:
    """Unassigned rows come from the export root, wired in a later milestone."""
    src = LocalDatasetSource(tmp_path / "t", tmp_path / "v")
    assert list(src.list("all", TaskEnum.detection, SplitEnum.unassigned)) == []


def test_local_source_fetch_to_local_returns_task_dir(tmp_path) -> None:
    train = tmp_path / "t"
    _write_dataset(train, "all", "detection", {"p1.png": []})
    src = LocalDatasetSource(train, tmp_path / "v")
    path = src.fetch_to_local("all", TaskEnum.detection, SplitEnum.train)
    assert path == train / "all" / "detection"


def _make_hf_source(tmp_path):
    """Build a HuggingFaceDatasetSource with a fake settings + token (M10)."""
    settings = MagicMock()
    settings.hf_cache_dir = None
    return HuggingFaceDatasetSource(settings, token="hf_test_token")


def test_huggingface_source_satisfies_protocol(tmp_path) -> None:
    """M10 real impl: HuggingFaceDatasetSource still satisfies IDatasetSource."""
    src = _make_hf_source(tmp_path)
    assert isinstance(src, IDatasetSource)
    assert src.name == "huggingface"


def test_huggingface_source_list_raises_not_implemented(tmp_path) -> None:
    """list() is worker-side; the web process must not call it."""
    src = _make_hf_source(tmp_path)
    with pytest.raises(NotImplementedError):
        list(src.list("all", TaskEnum.detection, SplitEnum.train))


def test_huggingface_source_fetch_to_local_raises_not_implemented(tmp_path) -> None:
    """fetch_to_local() without repo/revision raises NotImplementedError."""
    src = _make_hf_source(tmp_path)
    with pytest.raises(NotImplementedError):
        src.fetch_to_local("all", TaskEnum.detection, SplitEnum.train)
