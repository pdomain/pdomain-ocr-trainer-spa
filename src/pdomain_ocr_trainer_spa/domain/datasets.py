"""Dataset-kanban domain layer (spec 05-dataset-kanban).

Pure functions over :class:`Settings`, mirroring ``domain/profiles.py`` — no
AppState coupling, no ``pdomain_ocr_training`` import (the backend stays torch-free).

Covers the **recognition** and **detection** tasks. Recognition chips are
crops (``labels.json`` value is the label text); detection chips are pages
(``labels.json`` value is opaque DocTR ``DetectionDataset`` metadata — a dict
carrying ``polygons``). The classifier kanbans land in M12. The wire models
live in ``core/models.py``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from pdomain_ocr_trainer_spa.core.enums import TaskEnum
from pdomain_ocr_trainer_spa.core.errors import AppError
from pdomain_ocr_trainer_spa.core.models import (
    KanbanColumn,
    KanbanPageChip,
    KanbanProjectRow,
    KanbanView,
)
from pdomain_ocr_trainer_spa.domain.profiles import normalize_profile_name

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.core.models import ApplyAssignmentRequest
    from pdomain_ocr_trainer_spa.settings import Settings

_SPLIT_DIRS = ("train", "val")
_COLUMNS = ("unassigned", "train", "val")
_SUPPORTED_TASKS = (TaskEnum.recognition, TaskEnum.detection)

# labels.json values are heterogeneous by task: a string (recognition) or an
# opaque DocTR metadata object (detection). The domain layer treats them as
# opaque blobs except for the task-specific chip rendering / change-summary.
LabelMap = dict[str, object]


# ---------------------------------------------------------------------------
# naming helpers (verbatim semantics from pdomain_ocr_training.datasets)
# ---------------------------------------------------------------------------


def project_from_stem(stem: str) -> str:
    """Strip trailing digit-only segments from an image stem to recover the project ID."""
    parts = stem.split("_")
    end = len(parts)
    while end > 1 and parts[end - 1].isdigit():
        end -= 1
    return "_".join(parts[:end])


def _project_of(item_name: str) -> str:
    """Recover the project id for a crop / page filename."""
    return project_from_stem(Path(item_name).stem)


def _require_supported(task: TaskEnum) -> None:
    """Reject any task the kanban does not implement yet (classifier tasks → M12)."""
    if task not in _SUPPORTED_TASKS:
        raise AppError(
            code="dataset.task_unsupported",
            message=f"Task {task.value!r} kanban is not implemented yet",
            status_code=501,
        )


# ---------------------------------------------------------------------------
# task-specific rendering of a labels.json value
# ---------------------------------------------------------------------------


def _bbox_count(meta: object) -> int:
    """Best-effort bounding-box count from a detection ``labels.json`` value.

    DocTR ``DetectionDataset`` labels carry a ``polygons`` list; a bare list is
    treated as the polygon list directly. Anything else counts as zero.
    """
    if isinstance(meta, dict):
        polygons = meta.get("polygons")
        return len(polygons) if isinstance(polygons, list) else 0
    if isinstance(meta, list):
        return len(meta)
    return 0


def _chip_label(task: TaskEnum, value: object) -> str:
    """Render the chip's ``label_text`` for a labels.json value.

    Recognition → the literal label string. Detection → an ``"N bboxes"``
    summary so the chip stays informative without exposing raw geometry.
    """
    if task is TaskEnum.recognition:
        return str(value)
    count = _bbox_count(value)
    return f"{count} bbox" if count == 1 else f"{count} bboxes"


def _values_equal(task: TaskEnum, left: object, right: object) -> bool:
    """Compare two labels.json values for the "changed" highlight (spec 05 §6).

    Recognition compares the label text; detection compares the bbox set
    structurally (the whole metadata object).
    """
    if task is TaskEnum.recognition:
        return str(left) == str(right)
    return left == right


def _change_summary(task: TaskEnum, on_disk: object, export: object) -> str:
    """Human-readable ``change_summary`` for a changed chip (spec 05 §6)."""
    if task is TaskEnum.recognition:
        return f"label changed: {str(on_disk)!r} -> {str(export)!r}"
    before, after = _bbox_count(on_disk), _bbox_count(export)
    return f"bboxes changed: {before} -> {after}"


# ---------------------------------------------------------------------------
# disk access
# ---------------------------------------------------------------------------


def _split_root(settings: Settings, split: str, profile: str) -> Path:
    """Return ``<ml-{split}-dir>/<profile>``."""
    root = settings.ml_training_dir if split == "train" else settings.ml_validation_dir
    return root / profile


def _task_dir(settings: Settings, split: str, profile: str, task: TaskEnum) -> Path:
    """Return the on-disk task directory for a split."""
    return _split_root(settings, split, profile) / task.value


def _read_labels(task_dir: Path) -> LabelMap:
    """Read a ``labels.json`` (``{item_name: value}``); missing -> empty."""
    path = task_dir / "labels.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return {str(k): v for k, v in data.items()} if isinstance(data, dict) else {}


def _write_labels(task_dir: Path, labels: LabelMap) -> None:
    """Write a ``labels.json``."""
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")


def _iter_export_dirs(
    settings: Settings, profile: str, task: TaskEnum
) -> list[tuple[str, Path]]:
    """Return ``(project_id, task_dir)`` for every export matching ``profile``.

    Layout: ``<export-root>/<project_id>/<profile-subfolder>/<task>/``.
    A ``profile`` of ``all`` matches the ``all`` subfolder.
    """
    root = settings.labeler_export_root
    if root is None or not root.exists():
        return []
    found: list[tuple[str, Path]] = []
    for project_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for sub in sorted(s for s in project_dir.iterdir() if s.is_dir()):
            if normalize_profile_name(sub.name) != profile:
                continue
            task_path = sub / task.value
            if task_path.exists():
                found.append((project_dir.name, task_path))
    return found


# ---------------------------------------------------------------------------
# include-toggles persistence (the only persisted kanban state — spec 05 §5)
# ---------------------------------------------------------------------------


def _kanban_state_path(settings: Settings, profile: str) -> Path:
    """Path to a profile's ``kanban_state.json`` under the app-data root."""
    return settings.app_data_root / "profiles" / profile / "kanban_state.json"


def _read_include_toggles(settings: Settings, profile: str) -> tuple[bool, bool]:
    """Return the persisted ``(include_detection, include_recognition)`` — defaults True/True."""
    path = _kanban_state_path(settings, profile)
    if not path.exists():
        return (True, True)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return (True, True)
    return (
        bool(data.get("include_detection", True)),
        bool(data.get("include_recognition", True)),
    )


def set_include_toggles(
    settings: Settings,
    *,
    profile: str,
    include_detection: bool,
    include_recognition: bool,
) -> None:
    """Persist the include-toggles for a profile (spec 05 §5)."""
    normalized = normalize_profile_name(profile)
    path = _kanban_state_path(settings, normalized)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "include_detection": include_detection,
                "include_recognition": include_recognition,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# kanban view assembly
# ---------------------------------------------------------------------------


def _on_disk_chip(task: TaskEnum, item_name: str, value: object) -> KanbanPageChip:
    """Build a chip for an on-disk item (a crop for recognition, a page for detection)."""
    project = _project_of(item_name)
    is_recognition = task is TaskEnum.recognition
    return KanbanPageChip(
        key=f"{project}:{item_name}",
        page_name=item_name,
        crop_name=item_name if is_recognition else None,
        label_text=_chip_label(task, value),
        is_changed=False,
    )


def _rows_from_labels(
    task: TaskEnum, labels: LabelMap, source: str
) -> list[KanbanProjectRow]:
    """Group a ``{item_name: value}`` map into ordered project rows."""
    by_project: dict[str, list[KanbanPageChip]] = {}
    for item_name, value in sorted(labels.items()):
        chip = _on_disk_chip(task, item_name, value)
        by_project.setdefault(_project_of(item_name), []).append(chip)
    rows: list[KanbanProjectRow] = []
    for project_id in sorted(by_project):
        chips = by_project[project_id]
        rows.append(
            KanbanProjectRow(
                project_id=project_id,
                source="on_disk" if source == "on_disk" else "pending",
                page_count=len(chips),
                is_changed=any(c.is_changed for c in chips),
                style_tags=[],
                pages=chips,
            )
        )
    return rows


def _on_disk_labels(
    settings: Settings, split: str, profile: str, task: TaskEnum
) -> LabelMap:
    """All on-disk labels for a split."""
    return _read_labels(_task_dir(settings, split, profile, task))


def _unassigned_rows(
    settings: Settings,
    profile: str,
    task: TaskEnum,
    on_disk: dict[str, LabelMap],
) -> list[KanbanProjectRow]:
    """Build pending (export-root) rows, suppressing exports fully present on disk.

    Mirrors ``ExportManager.scan``: a project whose every item already exists
    on disk *with an identical value* is omitted. An item present on disk with a
    differing value is flagged ``is_changed`` and kept (spec 05 §6).
    """
    on_disk_labels: LabelMap = {}
    for split_labels in on_disk.values():
        on_disk_labels.update(split_labels)

    rows: list[KanbanProjectRow] = []
    for project_id, task_path in _iter_export_dirs(settings, profile, task):
        export_labels = _read_labels(task_path)
        if not export_labels:
            continue
        if all(
            name in on_disk_labels
            and _values_equal(task, on_disk_labels[name], value)
            for name, value in export_labels.items()
        ):
            continue  # fully present + unchanged — suppressed
        chips: list[KanbanPageChip] = []
        for item_name, value in sorted(export_labels.items()):
            is_changed = item_name in on_disk_labels and not _values_equal(
                task, on_disk_labels[item_name], value
            )
            summary = (
                _change_summary(task, on_disk_labels[item_name], value)
                if is_changed
                else None
            )
            is_recognition = task is TaskEnum.recognition
            chips.append(
                KanbanPageChip(
                    key=f"{project_id}:{item_name}",
                    page_name=item_name,
                    crop_name=item_name if is_recognition else None,
                    label_text=_chip_label(task, value),
                    is_changed=is_changed,
                    change_summary=summary,
                )
            )
        rows.append(
            KanbanProjectRow(
                project_id=project_id,
                source="pending",
                page_count=len(chips),
                is_changed=any(c.is_changed for c in chips),
                style_tags=[],
                pages=chips,
            )
        )
    return rows


def build_kanban(settings: Settings, *, profile: str, task: TaskEnum) -> KanbanView:
    """Assemble the committed ``KanbanView`` for a ``(profile, task)`` pair (spec 05 §2)."""
    _require_supported(task)
    normalized = normalize_profile_name(profile)
    on_disk = {
        split: _on_disk_labels(settings, split, normalized, task)
        for split in _SPLIT_DIRS
    }
    include_detection, include_recognition = _read_include_toggles(settings, normalized)
    return KanbanView(
        profile=normalized,
        task=task,
        columns={
            "unassigned": KanbanColumn(
                rows=_unassigned_rows(settings, normalized, task, on_disk)
            ),
            "train": KanbanColumn(
                rows=_rows_from_labels(task, on_disk["train"], "on_disk")
            ),
            "val": KanbanColumn(rows=_rows_from_labels(task, on_disk["val"], "on_disk")),
        },
        include_detection=include_detection,
        include_recognition=include_recognition,
    )


# ---------------------------------------------------------------------------
# apply — the single atomic commit (spec 05 §4)
# ---------------------------------------------------------------------------


def _committed_split_of(key: str, on_disk: dict[str, LabelMap]) -> str | None:
    """Return the committed column of a chip key, or ``None`` if not on disk."""
    item_name = key.split(":", 1)[1] if ":" in key else key
    for split in _SPLIT_DIRS:
        if item_name in on_disk[split]:
            return split
    return None


def _export_value_for(
    settings: Settings, profile: str, task: TaskEnum, key: str
) -> object | None:
    """Look up an export item's labels.json value by chip key."""
    project_id, _, item_name = key.partition(":")
    for export_project, task_path in _iter_export_dirs(settings, profile, task):
        if export_project != project_id:
            continue
        labels = _read_labels(task_path)
        if item_name in labels:
            return labels[item_name]
    return None


def _export_image_path(
    settings: Settings, profile: str, task: TaskEnum, key: str
) -> Path | None:
    """Locate the source image for an export chip key."""
    project_id, _, item_name = key.partition(":")
    for export_project, task_path in _iter_export_dirs(settings, profile, task):
        if export_project != project_id:
            continue
        candidate = task_path / "images" / item_name
        if candidate.exists():
            return candidate
    return None


# a sentinel distinct from a real labels.json value of ``None``
_MISSING: object = object()


def _apply_one(
    settings: Settings,
    profile: str,
    task: TaskEnum,
    key: str,
    target_split: str,
    on_disk: dict[str, LabelMap],
) -> None:
    """Commit one chip's staged move to disk (copy / move / delete).

    Raises on failure so the caller can record a per-key error.
    """
    item_name = key.split(":", 1)[1] if ":" in key else key
    committed = _committed_split_of(key, on_disk)

    if committed == target_split:
        return  # nothing staged for this chip

    if committed is None:
        # unassigned (export) -> train|val: copy image + label
        if target_split == "unassigned":
            return
        value = _export_value_for(settings, profile, task, key)
        src_img = _export_image_path(settings, profile, task, key)
        if value is None or src_img is None:
            raise AppError(
                code="dataset.apply_key_missing",
                message=f"No export found for {key!r}",
                status_code=404,
            )
        dest_dir = _task_dir(settings, target_split, profile, task)
        (dest_dir / "images").mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_img, dest_dir / "images" / item_name)
        labels = _read_labels(dest_dir)
        labels[item_name] = value
        _write_labels(dest_dir, labels)
        on_disk[target_split][item_name] = value
        return

    # on-disk item currently in `committed`
    src_dir = _task_dir(settings, committed, profile, task)
    src_value = on_disk[committed].get(item_name, _MISSING)

    if target_split == "unassigned":
        # delete from the committed split
        (src_dir / "images" / item_name).unlink(missing_ok=True)
        labels = _read_labels(src_dir)
        labels.pop(item_name, None)
        _write_labels(src_dir, labels)
        on_disk[committed].pop(item_name, None)
        return

    # train <-> val move
    dest_dir = _task_dir(settings, target_split, profile, task)
    (dest_dir / "images").mkdir(parents=True, exist_ok=True)
    src_img = src_dir / "images" / item_name
    if src_img.exists():
        shutil.move(str(src_img), str(dest_dir / "images" / item_name))
    dest_labels = _read_labels(dest_dir)
    dest_labels[item_name] = None if src_value is _MISSING else src_value
    _write_labels(dest_dir, dest_labels)
    src_labels = _read_labels(src_dir)
    src_labels.pop(item_name, None)
    _write_labels(src_dir, src_labels)
    on_disk[committed].pop(item_name, None)
    on_disk[target_split][item_name] = None if src_value is _MISSING else src_value


def apply_assignments(
    settings: Settings,
    *,
    profile: str,
    task: TaskEnum,
    request: ApplyAssignmentRequest,
    raise_on_total_failure: bool = False,
) -> tuple[KanbanView, list[dict[str, str]]]:
    """Commit a full staged assignment to disk (spec 05 §4).

    Best-effort and partial — a failed key does not abort the batch. Returns the
    freshly re-scanned :class:`KanbanView` and a list of ``{key, error}`` dicts.
    When ``raise_on_total_failure`` is set and *every* entry failed, raises a
    ``409 dataset.apply_failed`` :class:`AppError`.
    """
    _require_supported(task)
    normalized = normalize_profile_name(profile)
    on_disk = {
        split: _on_disk_labels(settings, split, normalized, task)
        for split in _SPLIT_DIRS
    }
    errors: list[dict[str, str]] = []
    attempted = 0
    for entry in request.assignments:
        if entry.target_split not in _COLUMNS:
            continue
        attempted += 1
        try:
            _apply_one(
                settings, normalized, task, entry.key, entry.target_split, on_disk
            )
        except (AppError, OSError, ValueError) as exc:
            errors.append({"key": entry.key, "error": str(exc)})

    if raise_on_total_failure and attempted > 0 and len(errors) == attempted:
        raise AppError(
            code="dataset.apply_failed",
            message="No assignment could be applied",
            status_code=409,
        )

    return build_kanban(settings, profile=normalized, task=task), errors
