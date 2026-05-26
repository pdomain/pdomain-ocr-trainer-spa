"""Profile discovery + CRUD over the on-disk dataset layout (spec 04)."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from pdomain_ocr_trainer_spa.core.enums import TypefaceEnum
from pdomain_ocr_trainer_spa.core.errors import AppError
from pdomain_ocr_trainer_spa.core.models import Profile, ProfileCounts

if TYPE_CHECKING:
    from pathlib import Path

    from pdomain_ocr_trainer_spa.settings import Settings

BASE_PROFILE = "all"
LEGACY_BASE_PROFILE = "base-ocr"
DATA_TASKS = ("detection", "recognition")
_TOML_KEY_ORDER = ("display_name", "language", "typeface", "notes")


def normalize_profile_name(name: str) -> str:
    """Normalize a profile name: lowercase, hyphenated, ``base-ocr``/empty -> ``all``."""
    value = (name or "").strip().lower().replace(" ", "-").replace("_", "-")
    if value == LEGACY_BASE_PROFILE:
        return BASE_PROFILE
    return value or BASE_PROFILE


def _parse_toml(path: Path) -> dict[str, object]:
    """Read a ``profile.toml`` into a dict; missing file -> empty dict."""
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _format_toml(data: dict[str, object]) -> str:
    """Serialize a profile.toml dict — known keys in stable order, unknown keys last."""
    lines: list[str] = []
    for key in _TOML_KEY_ORDER:
        value = data.get(key)
        if value is not None:
            lines.append(f'{key} = "{value}"')
    for key, value in data.items():
        if key in _TOML_KEY_ORDER or value is None:
            continue
        lines.append(f'{key} = "{value}"')
    return "\n".join(lines) + "\n" if lines else ""


def _write_toml(path: Path, data: dict[str, object]) -> None:
    """Write (or delete) a ``profile.toml`` — an empty payload removes the file."""
    body = _format_toml(data)
    if not body:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _profile_dirs(settings: Settings, name: str) -> tuple[Path, Path]:
    """Return the (training, validation) directories for a profile."""
    return (settings.ml_training_dir / name, settings.ml_validation_dir / name)


def _toml_paths(settings: Settings, name: str) -> tuple[Path, Path]:
    """Return the (training, validation) ``profile.toml`` paths for a profile."""
    train_dir, val_dir = _profile_dirs(settings, name)
    return (train_dir / "profile.toml", val_dir / "profile.toml")


def _discover_names(settings: Settings) -> set[str]:
    """Discover every profile name from disk (spec 04 §1.1)."""
    names: set[str] = {BASE_PROFILE}
    for root in (settings.ml_training_dir, settings.ml_validation_dir):
        if not root.exists():
            continue
        for child in root.iterdir():
            if child.is_dir():
                names.add(normalize_profile_name(child.name))
    if settings.shared_models_dir.exists():
        for child in settings.shared_models_dir.iterdir():
            if child.is_dir():
                names.add(normalize_profile_name(child.name))
    if settings.labeler_export_root is not None and settings.labeler_export_root.exists():
        for child in settings.labeler_export_root.iterdir():
            if child.is_dir():
                names.add(normalize_profile_name(child.name))
    return names


def _task_dir(settings: Settings, split: str, name: str, task: str) -> Path:
    """Return ``<ml-{split}-dir>/<name>/<task>``."""
    root = settings.ml_training_dir if split == "train" else settings.ml_validation_dir
    return root / name / task


def _has_task_data(settings: Settings, split: str, name: str, task: str) -> bool:
    """True when a task directory holds a ``labels.json`` or ``metadata.jsonl``."""
    task_dir = _task_dir(settings, split, name, task)
    return (task_dir / "labels.json").exists() or (task_dir / "metadata.jsonl").exists()


def _count_entries(settings: Settings, split: str, name: str, task: str) -> int:
    """Count rows for a task split — labels.json keys or metadata.jsonl lines."""
    task_dir = _task_dir(settings, split, name, task)
    labels = task_dir / "labels.json"
    if labels.exists():
        import json

        try:
            data = json.loads(labels.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return 0
        return len(data) if isinstance(data, dict) else 0
    metadata = task_dir / "metadata.jsonl"
    if metadata.exists():
        return sum(1 for line in metadata.read_text(encoding="utf-8").splitlines() if line.strip())
    return 0


def _build_counts(settings: Settings, name: str) -> ProfileCounts:
    """Compute per-task page / crop counts for a profile."""
    return ProfileCounts(
        detection_train_pages=_count_entries(settings, "train", name, "detection"),
        detection_val_pages=_count_entries(settings, "val", name, "detection"),
        recognition_train_crops=_count_entries(settings, "train", name, "recognition"),
        recognition_val_crops=_count_entries(settings, "val", name, "recognition"),
        typeface_train_crops=_count_entries(settings, "train", name, "typeface"),
        typeface_val_crops=_count_entries(settings, "val", name, "typeface"),
        glyph_train_crops=_count_entries(settings, "train", name, "glyph"),
        glyph_val_crops=_count_entries(settings, "val", name, "glyph"),
    )


def _coerce_typeface(value: object) -> TypefaceEnum | None:
    """Coerce a raw toml value into a TypefaceEnum, ignoring unknown values."""
    if value is None:
        return None
    try:
        return TypefaceEnum(str(value))
    except ValueError:
        return None


def _load_metadata(settings: Settings, name: str) -> dict[str, object]:
    """Load + reconcile training/validation ``profile.toml`` (409 on conflict)."""
    train_path, val_path = _toml_paths(settings, name)
    train_data = _parse_toml(train_path)
    val_data = _parse_toml(val_path)
    if train_data and val_data and train_data != val_data:
        raise AppError(
            code="profile.toml.conflict",
            message=f"profile.toml mismatch for {name!r}",
            status_code=409,
        )
    return train_data or val_data


def build_profile(settings: Settings, name: str) -> Profile:
    """Assemble a Profile model from on-disk state."""
    normalized = normalize_profile_name(name)
    metadata = _load_metadata(settings, normalized)
    raw_display = metadata.get("display_name")
    display_name = str(raw_display) if raw_display else normalized
    language = metadata.get("language")
    has_train = any(_has_task_data(settings, "train", normalized, t) for t in DATA_TASKS)
    has_val = any(_has_task_data(settings, "val", normalized, t) for t in DATA_TASKS)
    return Profile(
        name=normalized,
        display_name=display_name,
        language=str(language) if language else None,
        typeface=_coerce_typeface(metadata.get("typeface")),
        is_base=normalized == BASE_PROFILE,
        has_training_data=has_train,
        has_validation_data=has_val,
        counts=_build_counts(settings, normalized),
    )


def list_profiles(settings: Settings) -> list[Profile]:
    """Return every discovered profile, sorted by name."""
    return [build_profile(settings, n) for n in sorted(_discover_names(settings))]


def get_profile(settings: Settings, name: str) -> Profile:
    """Return one profile by name; 404 when not discovered."""
    normalized = normalize_profile_name(name)
    if normalized not in _discover_names(settings):
        raise AppError(
            code="profile.not_found",
            message=f"No profile named {normalized!r}",
            status_code=404,
        )
    return build_profile(settings, normalized)


def _metadata_payload(
    display_name: str | None,
    language: str | None,
    typeface: TypefaceEnum | None,
    notes: str | None,
) -> dict[str, object]:
    """Build a profile.toml dict, dropping unset (None) fields."""
    payload: dict[str, object] = {}
    if display_name is not None:
        payload["display_name"] = display_name
    if language is not None:
        payload["language"] = language
    if typeface is not None:
        payload["typeface"] = typeface.value
    if notes is not None:
        payload["notes"] = notes
    return payload


def create_profile(
    settings: Settings,
    *,
    name: str,
    display_name: str | None = None,
    language: str | None = None,
    typeface: TypefaceEnum | None = None,
    notes: str | None = None,
) -> Profile:
    """Create a profile — make its dataset dirs and (optionally) profile.toml."""
    normalized = normalize_profile_name(name)
    if normalized in _discover_names(settings):
        raise AppError(
            code="profile.exists",
            message=f"Profile {normalized!r} already exists",
            status_code=409,
        )
    train_dir, val_dir = _profile_dirs(settings, normalized)
    train_dir.mkdir(parents=True, exist_ok=True)
    val_dir.mkdir(parents=True, exist_ok=True)
    has_metadata = any(v is not None for v in (language, typeface, notes)) or (
        display_name is not None and normalize_profile_name(display_name) != normalized
    )
    if has_metadata:
        payload = _metadata_payload(display_name or name, language, typeface, notes)
        for path in _toml_paths(settings, normalized):
            _write_toml(path, payload)
    return build_profile(settings, normalized)


def update_profile(
    settings: Settings,
    name: str,
    *,
    fields: dict[str, object],
) -> Profile:
    """PATCH a profile's metadata. ``None`` clears a field; both files stay in sync."""
    profile = get_profile(settings, name)
    normalized = profile.name
    metadata = _load_metadata(settings, normalized)
    metadata.setdefault("display_name", profile.display_name)
    for key in ("display_name", "language", "typeface", "notes"):
        if key not in fields:
            continue
        value = fields[key]
        if value is None:
            metadata.pop(key, None)
        elif key == "typeface":
            coerced = _coerce_typeface(value)
            if coerced is None:
                raise AppError(
                    code="profile.bad_typeface",
                    message=f"Unknown typeface {value!r}",
                    status_code=422,
                )
            metadata[key] = coerced.value
        else:
            metadata[key] = str(value)
    if set(metadata) == {"display_name"} and metadata["display_name"] == normalized:
        metadata = {}
    for path in _toml_paths(settings, normalized):
        _write_toml(path, metadata)
    return build_profile(settings, normalized)


def delete_profile(settings: Settings, name: str) -> None:
    """Delete a profile. Refuses ``all`` (409) and any profile with data (409)."""
    profile = get_profile(settings, name)
    normalized = profile.name
    if normalized == BASE_PROFILE:
        raise AppError(
            code="profile.is_base",
            message="The 'all' profile cannot be deleted",
            status_code=409,
        )
    if _profile_has_data(settings, normalized):
        raise AppError(
            code="profile.has_data",
            message=f"Profile {normalized!r} has datasets and cannot be deleted",
            status_code=409,
        )
    # Non-terminal-run guard (spec 04 §1.5) lands with the runs registry in M6.
    _remove_empty_profile(settings, normalized)


def _profile_has_data(settings: Settings, name: str) -> bool:
    """True when a profile holds detection/recognition labels or non-empty models."""
    for split in ("train", "val"):
        for task in ("detection", "recognition", "typeface", "glyph"):
            if _has_task_data(settings, split, name, task):
                return True
    models_dir = settings.shared_models_dir / name
    return models_dir.exists() and any(models_dir.iterdir())


def _remove_empty_profile(settings: Settings, name: str) -> None:
    """Remove a profile's empty training/validation dirs and empty model dir."""
    import shutil

    for directory in _profile_dirs(settings, name):
        if directory.exists():
            shutil.rmtree(directory)
    models_dir = settings.shared_models_dir / name
    if models_dir.exists() and not any(models_dir.iterdir()):
        models_dir.rmdir()


def has_legacy_layout(settings: Settings) -> bool:
    """True when a legacy flat ``ml-training/{detection,recognition}`` layout exists."""
    return any((settings.ml_training_dir / task).is_dir() for task in DATA_TASKS)


def migrate_legacy(settings: Settings) -> None:
    """Move the legacy flat layout into ``<ml-dir>/all/{detection,recognition}``."""
    for root in (settings.ml_training_dir, settings.ml_validation_dir):
        for task in DATA_TASKS:
            flat = root / task
            if not flat.is_dir():
                continue
            target = root / BASE_PROFILE / task
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():  # pragma: no cover — idempotent guard
                continue
            flat.rename(target)
