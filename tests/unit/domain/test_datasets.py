"""Domain-layer tests for the recognition dataset kanban (spec 05 §11)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from pdomain_ocr_trainer_spa.core.enums import TaskEnum
from pdomain_ocr_trainer_spa.core.errors import AppError
from pdomain_ocr_trainer_spa.core.models import ApplyAssignmentRequest, AssignmentEntry
from pdomain_ocr_trainer_spa.domain import datasets as dom

if TYPE_CHECKING:
    from pathlib import Path

    from pdomain_ocr_trainer_spa.settings import Settings


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
        (det / "labels.json").write_text(json.dumps({p: [] for p in detection_pages}), encoding="utf-8")
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
    train_labels = export_settings.ml_training_dir / "all" / "recognition" / "labels.json"
    assert json.loads(train_labels.read_text()) == {"myproj_1_0.png": "hello"}
    assert (export_settings.ml_training_dir / "all" / "recognition" / "images" / "myproj_1_0.png").exists()
    assert [r.project_id for r in view.columns["train"].rows] == ["myproj"]
    assert view.columns["train"].rows[0].source == "on_disk"


def test_scenario_4_move_train_to_val(export_settings: Settings) -> None:
    _seed_on_disk(export_settings, "train", "all", {"p_1_0.png": "a", "p_1_1.png": "b"})
    req = ApplyAssignmentRequest(assignments=[AssignmentEntry(key="p:p_1_0.png", target_split="val")])
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
    assert (export_settings.ml_validation_dir / "all" / "recognition" / "images" / "p_1_0.png").exists()
    assert not (export_settings.ml_training_dir / "all" / "recognition" / "images" / "p_1_0.png").exists()
    _ = view


def test_scenario_5_move_split_to_unassigned_deletes_files(export_settings: Settings) -> None:
    _seed_on_disk(export_settings, "val", "all", {"p_1_0.png": "a"})
    req = ApplyAssignmentRequest(assignments=[AssignmentEntry(key="p:p_1_0.png", target_split="unassigned")])
    view, errors = dom.apply_assignments(
        export_settings, profile="all", task=TaskEnum.recognition, request=req
    )
    assert errors == []
    val_labels = json.loads(
        (export_settings.ml_validation_dir / "all" / "recognition" / "labels.json").read_text()
    )
    assert val_labels == {}
    assert not (export_settings.ml_validation_dir / "all" / "recognition" / "images" / "p_1_0.png").exists()
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
    dom.set_include_toggles(export_settings, profile="all", include_detection=False, include_recognition=True)
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
    req = ApplyAssignmentRequest(assignments=[AssignmentEntry(key="ghost:ghost_1.png", target_split="train")])
    view, errors = dom.apply_assignments(
        export_settings, profile="all", task=TaskEnum.recognition, request=req
    )
    assert [e["key"] for e in errors] == ["ghost:ghost_1.png"]
    _ = view


def test_apply_all_failed_raises_409(export_settings: Settings) -> None:
    req = ApplyAssignmentRequest(assignments=[AssignmentEntry(key="ghost:ghost_1.png", target_split="train")])
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


def test_classifier_task_rejected(export_settings: Settings) -> None:
    with pytest.raises(AppError) as excinfo:
        dom.build_kanban(export_settings, profile="all", task=TaskEnum.typeface_classification)
    assert excinfo.value.code == "dataset.task_unsupported"
    assert excinfo.value.status_code == 501


# ---------------------------------------------------------------------------
# detection task (spec 05 — page chips with bbox counts)
# ---------------------------------------------------------------------------


def _det_meta(n_boxes: int) -> dict[str, object]:
    """A DocTR DetectionDataset labels.json value with ``n_boxes`` polygons."""
    return {
        "img_dimensions": [100, 100],
        "polygons": [[[0, 0], [1, 0], [1, 1], [0, 1]] for _ in range(n_boxes)],
    }


def _write_detection_labels(task_dir: Path, labels: dict[str, dict[str, object]]) -> None:
    """Write a detection ``labels.json`` + matching page images into ``task_dir``."""
    images = task_dir / "images"
    images.mkdir(parents=True, exist_ok=True)
    (task_dir / "labels.json").write_text(json.dumps(labels), encoding="utf-8")
    for page_name in labels:
        (images / page_name).write_bytes(b"png")


def _seed_detection_export(settings: Settings, project_id: str, labels: dict[str, dict[str, object]]) -> None:
    """Drop a labeler DocTR detection export for ``project_id``."""
    assert settings.labeler_export_root is not None
    base = settings.labeler_export_root / project_id / "all" / "detection"
    _write_detection_labels(base, labels)


def _seed_detection_on_disk(
    settings: Settings, split: str, profile: str, labels: dict[str, dict[str, object]]
) -> None:
    """Seed an on-disk detection split for ``profile``."""
    root = settings.ml_training_dir if split == "train" else settings.ml_validation_dir
    _write_detection_labels(root / profile / "detection", labels)


def test_detection_export_appears_in_unassigned_with_bbox_count(
    export_settings: Settings,
) -> None:
    _seed_detection_export(export_settings, "myproj", {"myproj_1.png": _det_meta(3)})
    view = dom.build_kanban(export_settings, profile="all", task=TaskEnum.detection)
    rows = view.columns["unassigned"].rows
    assert [r.project_id for r in rows] == ["myproj"]
    chip = rows[0].pages[0]
    assert chip.page_name == "myproj_1.png"
    assert chip.crop_name is None  # detection chips are pages, not crops
    assert chip.label_text == "3 bboxes"
    assert chip.key == "myproj:myproj_1.png"


def test_detection_single_bbox_label_is_singular(export_settings: Settings) -> None:
    _seed_detection_export(export_settings, "p", {"p_1.png": _det_meta(1)})
    view = dom.build_kanban(export_settings, profile="all", task=TaskEnum.detection)
    assert view.columns["unassigned"].rows[0].pages[0].label_text == "1 bbox"


def test_detection_apply_copies_export_into_train_with_valid_labels(
    export_settings: Settings,
) -> None:
    meta = _det_meta(2)
    _seed_detection_export(export_settings, "myproj", {"myproj_1.png": meta})
    req = ApplyAssignmentRequest(
        assignments=[AssignmentEntry(key="myproj:myproj_1.png", target_split="train")]
    )
    view, errors = dom.apply_assignments(export_settings, profile="all", task=TaskEnum.detection, request=req)
    assert errors == []
    train_labels = export_settings.ml_training_dir / "all" / "detection" / "labels.json"
    assert json.loads(train_labels.read_text()) == {"myproj_1.png": meta}
    assert (export_settings.ml_training_dir / "all" / "detection" / "images" / "myproj_1.png").exists()
    assert [r.project_id for r in view.columns["train"].rows] == ["myproj"]


def test_detection_move_train_to_val_preserves_metadata(
    export_settings: Settings,
) -> None:
    meta = _det_meta(4)
    _seed_detection_on_disk(export_settings, "train", "all", {"p_1.png": meta})
    req = ApplyAssignmentRequest(assignments=[AssignmentEntry(key="p:p_1.png", target_split="val")])
    _view, errors = dom.apply_assignments(
        export_settings, profile="all", task=TaskEnum.detection, request=req
    )
    assert errors == []
    val_labels = json.loads(
        (export_settings.ml_validation_dir / "all" / "detection" / "labels.json").read_text()
    )
    assert val_labels == {"p_1.png": meta}
    assert not (export_settings.ml_training_dir / "all" / "detection" / "images" / "p_1.png").exists()


def test_detection_move_to_unassigned_deletes_files(
    export_settings: Settings,
) -> None:
    _seed_detection_on_disk(export_settings, "val", "all", {"p_1.png": _det_meta(1)})
    req = ApplyAssignmentRequest(assignments=[AssignmentEntry(key="p:p_1.png", target_split="unassigned")])
    view, errors = dom.apply_assignments(export_settings, profile="all", task=TaskEnum.detection, request=req)
    assert errors == []
    val_labels = json.loads(
        (export_settings.ml_validation_dir / "all" / "detection" / "labels.json").read_text()
    )
    assert val_labels == {}
    assert not view.columns["val"].rows


def test_detection_changed_highlight_on_differing_bbox_set(
    export_settings: Settings,
) -> None:
    _seed_detection_on_disk(export_settings, "train", "all", {"p_1.png": _det_meta(2)})
    _seed_detection_export(export_settings, "p", {"p_1.png": _det_meta(5)})
    view = dom.build_kanban(export_settings, profile="all", task=TaskEnum.detection)
    chip = view.columns["unassigned"].rows[0].pages[0]
    assert chip.is_changed is True
    assert chip.change_summary is not None
    assert "2" in chip.change_summary
    assert "5" in chip.change_summary


def test_detection_unchanged_export_is_suppressed(export_settings: Settings) -> None:
    meta = _det_meta(3)
    _seed_detection_on_disk(export_settings, "train", "all", {"p_1.png": meta})
    _seed_detection_export(export_settings, "p", {"p_1.png": meta})
    view = dom.build_kanban(export_settings, profile="all", task=TaskEnum.detection)
    assert not view.columns["unassigned"].rows


# ---------------------------------------------------------------------------
# Track D: manifest-based freshness (is_fresh)
# ---------------------------------------------------------------------------


def _write_manifest(export_root: Path, exported_at: str, project_id: str) -> None:
    """Write a minimal manifest.json into export_root."""
    import json

    manifest = {
        "schema": "pdomain.doctr-export-manifest",
        "version": 1,
        "generated_at": "2026-06-10T12:00:00Z",
        "app": "pdomain-ocr-labeler-spa",
        "projects": {
            project_id: {
                "exported_at": exported_at,
                "page_count": 1,
                "tasks": {"recognition": {"item_count": 1}},
            }
        },
    }
    (export_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_fresh_flag_set_when_manifest_newer(
    export_settings: Settings,
) -> None:
    """Projects with a manifest exported_at newer than last-seen are flagged is_fresh."""
    _seed_export(export_settings, "myproj", {"myproj_0001.png": "test"})
    assert export_settings.labeler_export_root is not None
    _write_manifest(export_settings.labeler_export_root, "2026-06-10T11:00:00Z", "myproj")
    # No freshness record exists — first scan → is_fresh
    view = dom.build_kanban(export_settings, profile="all", task=TaskEnum.recognition)
    unassigned = view.columns["unassigned"].rows
    assert len(unassigned) == 1
    assert unassigned[0].project_id == "myproj"
    assert unassigned[0].is_fresh is True


def test_fresh_flag_not_set_when_seen_at_matches(
    export_settings: Settings,
) -> None:
    """Projects where exported_at == last-seen are not flagged is_fresh."""
    from pdomain_ocr_trainer_spa.domain.labeler_export import ExportFreshnessRecord

    _seed_export(export_settings, "myproj", {"myproj_0001.png": "test"})
    assert export_settings.labeler_export_root is not None
    _write_manifest(export_settings.labeler_export_root, "2026-06-10T11:00:00Z", "myproj")
    # Pre-seed the freshness record with the same timestamp
    rec = ExportFreshnessRecord(project_seen_at={"myproj": "2026-06-10T11:00:00+00:00"})
    freshness_path = export_settings.app_data_root / "profiles" / "all" / "freshness_state.json"
    freshness_path.parent.mkdir(parents=True, exist_ok=True)
    rec.save(freshness_path)
    view = dom.build_kanban(export_settings, profile="all", task=TaskEnum.recognition)
    unassigned = view.columns["unassigned"].rows
    assert not any(r.is_fresh for r in unassigned)


def test_no_manifest_no_fresh_flag(export_settings: Settings) -> None:
    """When no manifest.json exists, is_fresh is always False (zero regression)."""
    _seed_export(export_settings, "myproj", {"myproj_0001.png": "test"})
    # No manifest.json written
    view = dom.build_kanban(export_settings, profile="all", task=TaskEnum.recognition)
    unassigned = view.columns["unassigned"].rows
    assert not any(r.is_fresh for r in unassigned)


def test_freshness_record_updated_after_build(
    export_settings: Settings,
) -> None:
    """build_kanban persists the seen timestamp so the next scan does not re-flag."""
    _seed_export(export_settings, "myproj", {"myproj_0001.png": "x"})
    assert export_settings.labeler_export_root is not None
    _write_manifest(export_settings.labeler_export_root, "2026-06-10T11:00:00Z", "myproj")
    # First scan — fresh
    dom.build_kanban(export_settings, profile="all", task=TaskEnum.recognition)
    # Second scan — record was persisted, no longer fresh
    view2 = dom.build_kanban(export_settings, profile="all", task=TaskEnum.recognition)
    assert not any(r.is_fresh for r in view2.columns["unassigned"].rows)


# ---------------------------------------------------------------------------
# Bug-fix: non-UTC offset produces false freshness
# ---------------------------------------------------------------------------


def test_normalize_exported_at_converts_to_utc() -> None:
    """_normalize_exported_at must produce a UTC-normalised ISO string.

    _normalize_exported_at accepts proj_data — either a dict {"exported_at": ...}
    or an object with an .exported_at attribute. Two proj_data objects carrying
    the SAME instant in different offsets must normalise to equal UTC strings.
    """
    from datetime import UTC, datetime, timedelta, timezone

    from pdomain_ocr_trainer_spa.domain.datasets import _normalize_exported_at

    # 2026-06-10T11:00:00+05:30 == 2026-06-10T05:30:00+00:00
    ist = timezone(timedelta(hours=5, minutes=30))
    dt_ist = datetime(2026, 6, 10, 11, 0, 0, tzinfo=ist)
    dt_utc = datetime(2026, 6, 10, 5, 30, 0, tzinfo=UTC)

    # Test via dict representation (fallback branch)
    result_dict_ist = _normalize_exported_at({"exported_at": dt_ist})
    result_dict_utc = _normalize_exported_at({"exported_at": dt_utc})
    assert result_dict_ist == result_dict_utc, (
        f"Dict-carried same instant with different offsets must normalise equally; "
        f"got {result_dict_ist!r} vs {result_dict_utc!r}"
    )
    assert "+00:00" in result_dict_ist, f"Expected UTC offset in result, got {result_dict_ist!r}"

    # Test via string representation (ISO 8601 with non-UTC offset, from fallback JSON)
    str_ist = dt_ist.isoformat()  # "2026-06-10T11:00:00+05:30"
    str_utc = dt_utc.isoformat()  # "2026-06-10T05:30:00+00:00"
    result_str_ist = _normalize_exported_at({"exported_at": str_ist})
    result_str_utc = _normalize_exported_at({"exported_at": str_utc})
    assert result_str_ist == result_str_utc, (
        f"String-carried same instant with different offsets must normalise equally; "
        f"got {result_str_ist!r} vs {result_str_utc!r}"
    )


def test_non_utc_offset_not_false_fresh(export_settings: Settings) -> None:
    """A manifest exported_at with +05:30 equal to the stored UTC is NOT fresh.

    This is the primary regression test: a non-UTC offset for the SAME instant
    as the persisted UTC string used to compare lexicographically greater
    ("+05" > "+00") and falsely flag the project as fresh.
    """
    from datetime import UTC, datetime, timedelta, timezone

    from pdomain_ocr_trainer_spa.domain.datasets import _normalize_exported_at
    from pdomain_ocr_trainer_spa.domain.labeler_export import ExportFreshnessRecord

    _seed_export(export_settings, "myproj", {"myproj_0001.png": "test"})
    assert export_settings.labeler_export_root is not None

    # The instant: 2026-06-10T11:00:00+05:30 == 2026-06-10T05:30:00Z
    ist = timezone(timedelta(hours=5, minutes=30))
    instant_ist = datetime(2026, 6, 10, 11, 0, 0, tzinfo=ist)
    instant_utc = datetime(2026, 6, 10, 5, 30, 0, tzinfo=UTC)

    # Persist the freshness record using the UTC representation.
    # _normalize_exported_at takes proj_data (a dict or object with .exported_at),
    # not a bare datetime — wrap in a dict so it resolves correctly.
    stored_utc_str = _normalize_exported_at({"exported_at": instant_utc})
    rec = ExportFreshnessRecord(project_seen_at={"myproj": stored_utc_str})
    freshness_path = export_settings.app_data_root / "profiles" / "all" / "freshness_state.json"
    freshness_path.parent.mkdir(parents=True, exist_ok=True)
    rec.save(freshness_path)

    # The manifest carries the same instant in +05:30 — should NOT be fresh
    _write_manifest(
        export_settings.labeler_export_root,
        instant_ist.isoformat(),  # "+05:30" string in manifest
        "myproj",
    )

    view = dom.build_kanban(export_settings, profile="all", task=TaskEnum.recognition)
    unassigned = view.columns["unassigned"].rows
    assert not any(r.is_fresh for r in unassigned), (
        "A manifest timestamp with +05:30 equal to the stored UTC must NOT be is_fresh; "
        f"got: {[r.project_id for r in unassigned if r.is_fresh]}"
    )
