"""Domain-layer tests for the recognition dataset kanban (spec 05 §11)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from pd_ocr_trainer_spa.core.enums import TaskEnum
from pd_ocr_trainer_spa.core.errors import AppError
from pd_ocr_trainer_spa.core.models import ApplyAssignmentRequest, AssignmentEntry
from pd_ocr_trainer_spa.domain import datasets as dom

if TYPE_CHECKING:
    from pathlib import Path

    from pd_ocr_trainer_spa.settings import Settings


def _write_recognition_labels(task_dir: Path, labels: dict[str, str]) -> None:
    """Write a recognition ``labels.json`` + matching image files into ``task_dir``."""
    images = task_dir / "images"
    images.mkdir(parents=True, exist_ok=True)
    (task_dir / "labels.json").write_text(json.dumps(labels), encoding="utf-8")
    for crop_name in labels:
        (images / crop_name).write_bytes(b"png")


def _seed_export(
    settings: Settings,
    project_id: str,
    labels: dict[str, str],
    *,
    detection_pages: list[str] | None = None,
) -> None:
    """Drop a labeler DocTR export for ``project_id`` under the export root."""
    assert settings.labeler_export_root is not None
    base = settings.labeler_export_root / project_id / "all"
    _write_recognition_labels(base / "recognition", labels)
    if detection_pages is not None:
        det = base / "detection"
        det_images = det / "images"
        det_images.mkdir(parents=True, exist_ok=True)
        (det / "labels.json").write_text(
            json.dumps({p: [] for p in detection_pages}), encoding="utf-8"
        )
        for page in detection_pages:
            (det_images / page).write_bytes(b"png")


def _seed_on_disk(settings: Settings, split: str, profile: str, labels: dict[str, str]) -> None:
    """Seed an on-disk recognition split for ``profile``."""
    root = settings.ml_training_dir if split == "train" else settings.ml_validation_dir
    _write_recognition_labels(root / profile / "recognition", labels)


@pytest.fixture
def export_settings(settings: Settings, tmp_path: Path) -> Settings:
    """Settings with a labeler export root configured."""
    return settings.model_copy(update={"labeler_export_root": tmp_path / "doctr-export"})


def test_empty_kanban_has_three_columns(export_settings: Settings) -> None:
    view = dom.build_kanban(export_settings, profile="all", task=TaskEnum.recognition)
    assert view.profile == "all"
    assert view.task is TaskEnum.recognition
    assert set(view.columns) == {"unassigned", "train", "val"}
    assert all(not col.rows for col in view.columns.values())


def test_scenario_1_export_appears_in_unassigned(export_settings: Settings) -> None:
    _seed_export(export_settings, "myproj", {"myproj_1_0.png": "hello"})
    view = dom.build_kanban(export_settings, profile="all", task=TaskEnum.recognition)
    rows = view.columns["unassigned"].rows
    assert [r.project_id for r in rows] == ["myproj"]
    assert rows[0].source == "pending"
    chip = rows[0].pages[0]
    assert chip.crop_name == "myproj_1_0.png"
    assert chip.label_text == "hello"
    assert chip.key == "myproj:myproj_1_0.png"


def test_on_disk_split_rows_are_on_disk_source(export_settings: Settings) -> None:
    _seed_on_disk(export_settings, "train", "all", {"proj_1_0.png": "world"})
    view = dom.build_kanban(export_settings, profile="all", task=TaskEnum.recognition)
    rows = view.columns["train"].rows
    assert [r.project_id for r in rows] == ["proj"]
    assert rows[0].source == "on_disk"
    assert rows[0].pages[0].crop_name == "proj_1_0.png"


def test_scenario_3_apply_copies_export_into_train(export_settings: Settings) -> None:
    _seed_export(export_settings, "myproj", {"myproj_1_0.png": "hello"})
    req = ApplyAssignmentRequest(
        assignments=[AssignmentEntry(key="myproj:myproj_1_0.png", target_split="train")]
    )
    view, errors = dom.apply_assignments(
        export_settings, profile="all", task=TaskEnum.recognition, request=req
    )
    assert errors == []
    train_labels = (
        export_settings.ml_training_dir / "all" / "recognition" / "labels.json"
    )
    assert json.loads(train_labels.read_text()) == {"myproj_1_0.png": "hello"}
    assert (
        export_settings.ml_training_dir / "all" / "recognition" / "images" / "myproj_1_0.png"
    ).exists()
    assert [r.project_id for r in view.columns["train"].rows] == ["myproj"]
    assert view.columns["train"].rows[0].source == "on_disk"


def test_scenario_4_move_train_to_val(export_settings: Settings) -> None:
    _seed_on_disk(export_settings, "train", "all", {"p_1_0.png": "a", "p_1_1.png": "b"})
    req = ApplyAssignmentRequest(
        assignments=[AssignmentEntry(key="p:p_1_0.png", target_split="val")]
    )
    view, errors = dom.apply_assignments(
        export_settings, profile="all", task=TaskEnum.recognition, request=req
    )
    assert errors == []
    train_labels = json.loads(
        (export_settings.ml_training_dir / "all" / "recognition" / "labels.json").read_text()
    )
    val_labels = json.loads(
        (export_settings.ml_validation_dir / "all" / "recognition" / "labels.json").read_text()
    )
    assert train_labels == {"p_1_1.png": "b"}
    assert val_labels == {"p_1_0.png": "a"}
    assert (
        export_settings.ml_validation_dir / "all" / "recognition" / "images" / "p_1_0.png"
    ).exists()
    assert not (
        export_settings.ml_training_dir / "all" / "recognition" / "images" / "p_1_0.png"
    ).exists()
    _ = view


def test_scenario_5_move_split_to_unassigned_deletes_files(export_settings: Settings) -> None:
    _seed_on_disk(export_settings, "val", "all", {"p_1_0.png": "a"})
    req = ApplyAssignmentRequest(
        assignments=[AssignmentEntry(key="p:p_1_0.png", target_split="unassigned")]
    )
    view, errors = dom.apply_assignments(
        export_settings, profile="all", task=TaskEnum.recognition, request=req
    )
    assert errors == []
    val_labels = json.loads(
        (export_settings.ml_validation_dir / "all" / "recognition" / "labels.json").read_text()
    )
    assert val_labels == {}
    assert not (
        export_settings.ml_validation_dir / "all" / "recognition" / "images" / "p_1_0.png"
    ).exists()
    assert not view.columns["val"].rows


def test_changed_highlight_flags_export_crop_differing_on_disk(
    export_settings: Settings,
) -> None:
    _seed_on_disk(export_settings, "train", "all", {"myproj_1_0.png": "old"})
    _seed_export(export_settings, "myproj", {"myproj_1_0.png": "new"})
    view = dom.build_kanban(export_settings, profile="all", task=TaskEnum.recognition)
    chip = view.columns["unassigned"].rows[0].pages[0]
    assert chip.is_changed is True
    assert chip.change_summary is not None
    assert "old" in chip.change_summary
    assert "new" in chip.change_summary


def test_unchanged_export_crop_not_flagged(export_settings: Settings) -> None:
    _seed_on_disk(export_settings, "train", "all", {"myproj_1_0.png": "same"})
    _seed_export(export_settings, "myproj", {"myproj_1_0.png": "same"})
    view = dom.build_kanban(export_settings, profile="all", task=TaskEnum.recognition)
    # An export crop already on disk with identical label is suppressed entirely
    # (legacy ExportManager.scan skips fully-present projects).
    assert not view.columns["unassigned"].rows


def test_include_toggles_persist_to_kanban_state_json(export_settings: Settings) -> None:
    dom.set_include_toggles(
        export_settings, profile="all", include_detection=False, include_recognition=True
    )
    state = export_settings.app_data_root / "profiles" / "all" / "kanban_state.json"
    assert json.loads(state.read_text()) == {
        "version": 2,
        "include_detection": False,
        "include_recognition": True,
    }
    view = dom.build_kanban(export_settings, profile="all", task=TaskEnum.recognition)
    assert view.include_detection is False
    assert view.include_recognition is True


def test_apply_unknown_key_reports_error(export_settings: Settings) -> None:
    req = ApplyAssignmentRequest(
        assignments=[AssignmentEntry(key="ghost:ghost_1.png", target_split="train")]
    )
    view, errors = dom.apply_assignments(
        export_settings, profile="all", task=TaskEnum.recognition, request=req
    )
    assert [e["key"] for e in errors] == ["ghost:ghost_1.png"]
    _ = view


def test_apply_all_failed_raises_409(export_settings: Settings) -> None:
    req = ApplyAssignmentRequest(
        assignments=[AssignmentEntry(key="ghost:ghost_1.png", target_split="train")]
    )
    with pytest.raises(AppError) as excinfo:
        dom.apply_assignments(
            export_settings,
            profile="all",
            task=TaskEnum.recognition,
            request=req,
            raise_on_total_failure=True,
        )
    assert excinfo.value.code == "dataset.apply_failed"
    assert excinfo.value.status_code == 409


def test_detection_task_rejected_in_m4(export_settings: Settings) -> None:
    with pytest.raises(AppError) as excinfo:
        dom.build_kanban(export_settings, profile="all", task=TaskEnum.detection)
    assert excinfo.value.code == "dataset.task_unsupported"
    assert excinfo.value.status_code == 501
