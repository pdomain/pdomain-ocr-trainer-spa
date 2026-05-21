"""Recognition dataset-kanban domain layer (spec 05-dataset-kanban).

Pure functions over :class:`Settings`, mirroring ``domain/profiles.py`` — no
AppState coupling, no ``pd_ocr_training`` import (the backend stays torch-free).

M4 implements the **recognition** task only; detection lands in M5 and the
classifier kanbans in M12. The wire models live in ``core/models.py``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from pd_ocr_trainer_spa.core.enums import TaskEnum
from pd_ocr_trainer_spa.core.errors import AppError
from pd_ocr_trainer_spa.core.models import (
    KanbanColumn,
    KanbanPageChip,
    KanbanProjectRow,
    KanbanView,
)
from pd_ocr_trainer_spa.domain.profiles import normalize_profile_name

if TYPE_CHECKING:
    from pd_ocr_trainer_spa.core.models import ApplyAssignmentRequest
    from pd_ocr_trainer_spa.settings import Settings

_SPLIT_DIRS = ("train", "val")
_COLUMNS = ("unassigned", "train", "val")


# ---------------------------------------------------------------------------
# naming helpers (verbatim semantics from pd_ocr_training.datasets)
# ---------------------------------------------------------------------------


def project_from_stem(stem: str) -> str:
    """Strip trailing digit-only segments from an image stem to recover the project ID."""
    parts = stem.split("_")
    end = len(parts)
    while end > 1 and parts[end - 1].isdigit():
        end -= 1
    return "_".join(parts[:end])


def _project_of(crop_name: str) -> str:
    """Recover the project id for a recognition crop filename."""
    return project_from_stem(Path(crop_name).stem)


def _require_recognition(task: TaskEnum) -> None:
    """Reject any task other than recognition — M4 is recognition-only."""
    if task is not TaskEnum.recognition:
        raise AppError(
            code="dataset.task_unsupported",
            message=f"Task {task.value!r} kanban is not implemented yet",
            status_code=501,
        )


# ---------------------------------------------------------------------------
# disk access
# ---------------------------------------------------------------------------


def _split_root(settings: Settings, split: str, profile: str) -> Path:
    """Return ``<ml-{split}-dir>/<profile>``."""
    root = settings.ml_training_dir if split == "train" else settings.ml_validation_dir
    return root / profile


def _recognition_dir(settings: Settings, split: str, profile: str) -> Path:
    """Return the on-disk recognition task directory for a split."""
    return _split_root(settings, split, profile) / "recognition"


def _read_labels(task_dir: Path) -> dict[str, str]:
    """Read a recognition ``labels.json`` (``{crop_name: label_text}``); missing -> empty."""
    path = task_dir / "labels.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def _write_labels(task_dir: Path, labels: dict[str, str]) -> None:
    """Write a recognition ``labels.json``."""
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")


def _iter_export_dirs(settings: Settings, profile: str) -> list[tuple[str, Path]]:
    """Return ``(project_id, recognition_dir)`` for every export matching ``profile``.

    Layout: ``<export-root>/<project_id>/<profile-subfolder>/recognition/``.
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
            recog = sub / "recognition"
            if recog.exists():
                found.append((project_dir.name, recog))
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


def _on_disk_chip(crop_name: str, label_text: str) -> KanbanPageChip:
    """Build a chip for an on-disk recognition crop."""
    project = _project_of(crop_name)
    return KanbanPageChip(
        key=f"{project}:{crop_name}",
        page_name=crop_name,
        crop_name=crop_name,
        label_text=label_text,
        is_changed=False,
    )


def _rows_from_labels(labels: dict[str, str], source: str) -> list[KanbanProjectRow]:
    """Group a ``{crop_name: label}`` map into ordered project rows."""
    by_project: dict[str, list[KanbanPageChip]] = {}
    for crop_name, label_text in sorted(labels.items()):
        chip = _on_disk_chip(crop_name, label_text)
        by_project.setdefault(_project_of(crop_name), []).append(chip)
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


def _on_disk_labels(settings: Settings, split: str, profile: str) -> dict[str, str]:
    """All on-disk recognition labels for a split."""
    return _read_labels(_recognition_dir(settings, split, profile))


def _unassigned_rows(
    settings: Settings,
    profile: str,
    on_disk: dict[str, dict[str, str]],
) -> list[KanbanProjectRow]:
    """Build pending (export-root) rows, suppressing exports fully present on disk.

    Mirrors ``ExportManager.scan``: a project whose every crop already exists
    on disk *with an identical label* is omitted. A crop present on disk with a
    differing label is flagged ``is_changed`` and kept (spec 05 §6).
    """
    on_disk_labels: dict[str, str] = {}
    for split_labels in on_disk.values():
        on_disk_labels.update(split_labels)

    rows: list[KanbanProjectRow] = []
    for project_id, recog_dir in _iter_export_dirs(settings, profile):
        export_labels = _read_labels(recog_dir)
        if not export_labels:
            continue
        if all(
            name in on_disk_labels and on_disk_labels[name] == text
            for name, text in export_labels.items()
        ):
            continue  # fully present + unchanged — suppressed
        chips: list[KanbanPageChip] = []
        for crop_name, label_text in sorted(export_labels.items()):
            is_changed = (
                crop_name in on_disk_labels and on_disk_labels[crop_name] != label_text
            )
            summary = (
                f"label changed: {on_disk_labels[crop_name]!r} -> {label_text!r}"
                if is_changed
                else None
            )
            chips.append(
                KanbanPageChip(
                    key=f"{project_id}:{crop_name}",
                    page_name=crop_name,
                    crop_name=crop_name,
                    label_text=label_text,
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
    _require_recognition(task)
    normalized = normalize_profile_name(profile)
    on_disk = {
        split: _on_disk_labels(settings, split, normalized) for split in _SPLIT_DIRS
    }
    include_detection, include_recognition = _read_include_toggles(settings, normalized)
    return KanbanView(
        profile=normalized,
        task=task,
        columns={
            "unassigned": KanbanColumn(rows=_unassigned_rows(settings, normalized, on_disk)),
            "train": KanbanColumn(rows=_rows_from_labels(on_disk["train"], "on_disk")),
            "val": KanbanColumn(rows=_rows_from_labels(on_disk["val"], "on_disk")),
        },
        include_detection=include_detection,
        include_recognition=include_recognition,
    )


# ---------------------------------------------------------------------------
# apply — the single atomic commit (spec 05 §4)
# ---------------------------------------------------------------------------


def _committed_split_of(key: str, on_disk: dict[str, dict[str, str]]) -> str | None:
    """Return the committed column of a chip key, or ``None`` if not on disk."""
    crop_name = key.split(":", 1)[1] if ":" in key else key
    for split in _SPLIT_DIRS:
        if crop_name in on_disk[split]:
            return split
    return None


def _export_label_for(settings: Settings, profile: str, key: str) -> str | None:
    """Look up an export crop's label text by chip key."""
    project_id, _, crop_name = key.partition(":")
    for export_project, recog_dir in _iter_export_dirs(settings, profile):
        if export_project != project_id:
            continue
        labels = _read_labels(recog_dir)
        if crop_name in labels:
            return labels[crop_name]
    return None


def _export_image_path(settings: Settings, profile: str, key: str) -> Path | None:
    """Locate the source image for an export chip key."""
    project_id, _, crop_name = key.partition(":")
    for export_project, recog_dir in _iter_export_dirs(settings, profile):
        if export_project != project_id:
            continue
        candidate = recog_dir / "images" / crop_name
        if candidate.exists():
            return candidate
    return None


def _apply_one(
    settings: Settings,
    profile: str,
    key: str,
    target_split: str,
    on_disk: dict[str, dict[str, str]],
) -> None:
    """Commit one chip's staged move to disk (copy / move / delete).

    Raises on failure so the caller can record a per-key error.
    """
    crop_name = key.split(":", 1)[1] if ":" in key else key
    committed = _committed_split_of(key, on_disk)

    if committed == target_split:
        return  # nothing staged for this chip

    if committed is None:
        # unassigned (export) -> train|val: copy image + label
        if target_split == "unassigned":
            return
        label = _export_label_for(settings, profile, key)
        src_img = _export_image_path(settings, profile, key)
        if label is None or src_img is None:
            raise AppError(
                code="dataset.apply_key_missing",
                message=f"No export found for {key!r}",
                status_code=404,
            )
        dest_dir = _recognition_dir(settings, target_split, profile)
        (dest_dir / "images").mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_img, dest_dir / "images" / crop_name)
        labels = _read_labels(dest_dir)
        labels[crop_name] = label
        _write_labels(dest_dir, labels)
        on_disk[target_split][crop_name] = label
        return

    # on-disk crop currently in `committed`
    src_dir = _recognition_dir(settings, committed, profile)
    src_label = on_disk[committed].get(crop_name, "")

    if target_split == "unassigned":
        # delete from the committed split
        (src_dir / "images" / crop_name).unlink(missing_ok=True)
        labels = _read_labels(src_dir)
        labels.pop(crop_name, None)
        _write_labels(src_dir, labels)
        on_disk[committed].pop(crop_name, None)
        return

    # train <-> val move
    dest_dir = _recognition_dir(settings, target_split, profile)
    (dest_dir / "images").mkdir(parents=True, exist_ok=True)
    src_img = src_dir / "images" / crop_name
    if src_img.exists():
        shutil.move(str(src_img), str(dest_dir / "images" / crop_name))
    dest_labels = _read_labels(dest_dir)
    dest_labels[crop_name] = src_label
    _write_labels(dest_dir, dest_labels)
    src_labels = _read_labels(src_dir)
    src_labels.pop(crop_name, None)
    _write_labels(src_dir, src_labels)
    on_disk[committed].pop(crop_name, None)
    on_disk[target_split][crop_name] = src_label


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
    _require_recognition(task)
    normalized = normalize_profile_name(profile)
    on_disk = {
        split: _on_disk_labels(settings, split, normalized) for split in _SPLIT_DIRS
    }
    errors: list[dict[str, str]] = []
    attempted = 0
    for entry in request.assignments:
        if entry.target_split not in _COLUMNS:
            continue
        attempted += 1
        try:
            _apply_one(settings, normalized, entry.key, entry.target_split, on_disk)
        except (AppError, OSError, ValueError) as exc:
            errors.append({"key": entry.key, "error": str(exc)})

    if raise_on_total_failure and attempted > 0 and len(errors) == attempted:
        raise AppError(
            code="dataset.apply_failed",
            message="No assignment could be applied",
            status_code=409,
        )

    return build_kanban(settings, profile=normalized, task=task), errors
