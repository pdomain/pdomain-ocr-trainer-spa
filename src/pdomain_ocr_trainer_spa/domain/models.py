"""Model-registry domain logic (spec 08-models).

This module owns the SPA-side model-name parser/formatter, sidecar
read/write/regenerate, and the rename / delete / patch operations layered on
top of the :class:`IModelRegistry` adapter. It is torch-free — model
*training* happens in the worker subprocess; this module only walks
``shared_models_dir`` and edits sidecars.

The new naming convention (D-T6, spec 08 §2) is::

    pd-{language}-{typeface}-{task}-{date}[-{qualifier}]

Legacy names (``pd-{profile}-{task}-...``) are parsed read-only — the SPA
displays, evaluates, and publishes them but never mints one.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pdomain_ocr_trainer_spa.core.enums import TaskEnum
from pdomain_ocr_trainer_spa.core.errors import AppError
from pdomain_ocr_trainer_spa.core.models import (
    ModelPaths,
    ModelSidecar,
    TrainedModel,
)
from pdomain_ocr_trainer_spa.domain.profiles import get_profile

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.core.models import Run
    from pdomain_ocr_trainer_spa.settings import Settings

_WEIGHT_SUFFIXES = (".pt", ".safetensors", ".bin")
_TASK_SLUGS = {t.value for t in TaskEnum}

# Recognised task tokens, longest-first so "typeface-classification" matches
# before the bare "classification" never appears as its own token.
_TASK_TOKENS = sorted(_TASK_SLUGS, key=len, reverse=True)


# ---------------------------------------------------------------------------
# model-name parsing (spec 08 §2)
# ---------------------------------------------------------------------------


@dataclass
class ParsedModelName:
    """The structured decomposition of a model name (spec 08 §2)."""

    prefix: str
    language: str | None
    typeface: str | None
    profile: str | None
    task: str
    qualifier: str
    is_legacy: bool


_NEW_NAME_RE = re.compile(
    r"^pd-(?P<language>[a-z]{2,3})-(?P<typeface>[a-z][a-z0-9-]*?)-"
    r"(?P<task>detection|recognition|typeface-classification|glyph-classification)"
    r"(?:-(?P<qualifier>.+))?$"
)


def parse_model_name(name: str) -> ParsedModelName:
    """Parse a model name into its structured parts (spec 08 §2).

    A name matching the new ``pd-{lang}-{typeface}-{task}[-{qualifier}]``
    convention is non-legacy; anything else with a recognised task token is
    treated as legacy (profile populated, language/typeface left ``None``).
    """
    new_match = _NEW_NAME_RE.match(name)
    if new_match is not None:
        return ParsedModelName(
            prefix="pd",
            language=new_match.group("language"),
            typeface=new_match.group("typeface"),
            profile=None,
            task=new_match.group("task"),
            qualifier=new_match.group("qualifier") or "",
            is_legacy=False,
        )

    # Legacy form: locate a task token anywhere in the name.
    tokens = name.split("-")
    task = ""
    task_idx = -1
    for idx, tok in enumerate(tokens):
        if tok in _TASK_SLUGS:
            task = tok
            task_idx = idx
            break
    profile = "-".join(tokens[1:task_idx]) if task_idx > 1 else None
    qualifier = "-".join(tokens[task_idx + 1 :]) if task_idx >= 0 else ""
    return ParsedModelName(
        prefix=tokens[0] if tokens else "",
        language=None,
        typeface=None,
        profile=profile,
        task=task,
        qualifier=qualifier,
        is_legacy=True,
    )


def is_valid_model_name(name: str) -> bool:
    """True when ``name`` follows the new convention or is a legacy task name."""
    parsed = parse_model_name(name)
    return bool(parsed.task) and parsed.task in _TASK_SLUGS


# ---------------------------------------------------------------------------
# sidecar build / write (spec 08 §3) — called by the worker on a done event
# ---------------------------------------------------------------------------


def build_sidecar_from_run(run: Run, *, doctr_arch: str | None = None) -> ModelSidecar:
    """Build the model sidecar for a finished training run (spec 08 §3)."""
    parsed = parse_model_name(run.model_name)
    return ModelSidecar(
        name=run.model_name,
        task=run.task.value,
        language=parsed.language,
        typeface=parsed.typeface,
        doctr_arch=doctr_arch,
        trained_at=run.finished_at or datetime.now(UTC),
        args=dict(run.args),
        qualifier=parsed.qualifier or None,
    )


def model_dir(settings: Settings, *, profile: str, task: TaskEnum, name: str) -> Path:
    """Return the on-disk leaf dir for a model (spec 08 §1)."""
    return settings.shared_models_dir / profile / task.value / name


def write_sidecar(settings: Settings, *, profile: str, sidecar: ModelSidecar) -> Path:
    """Write a model sidecar under ``shared_models_dir`` and return its path."""
    task = TaskEnum(sidecar.task)
    leaf = model_dir(settings, profile=profile, task=task, name=sidecar.name)
    leaf.mkdir(parents=True, exist_ok=True)
    sidecar_path = leaf / f"{sidecar.name}.metadata.json"
    sidecar_path.write_text(sidecar.model_dump_json(indent=2), encoding="utf-8")
    return sidecar_path


# ---------------------------------------------------------------------------
# discovery (spec 08 §1) — presence = a weights file OR a sidecar
# ---------------------------------------------------------------------------


def _weights_in(leaf: Path) -> Path | None:
    """Return the first recognised weights file in ``leaf``, or None."""
    if not leaf.is_dir():
        return None
    for child in sorted(leaf.iterdir()):
        if child.is_file() and child.suffix in _WEIGHT_SUFFIXES:
            return child
    return None


def _sidecar_path_in(leaf: Path) -> Path | None:
    """Return the ``*.metadata.json`` sidecar in ``leaf``, or None."""
    if not leaf.is_dir():
        return None
    matches = sorted(leaf.glob("*.metadata.json"))
    return matches[0] if matches else None


def _model_from_leaf(settings: Settings, leaf: Path, *, profile: str, task: TaskEnum) -> TrainedModel | None:
    """Build a :class:`TrainedModel` from one ``<profile>/<task>/<name>/`` dir."""
    weights = _weights_in(leaf)
    sidecar_path = _sidecar_path_in(leaf)
    if weights is None and sidecar_path is None:
        return None
    name = leaf.name
    config = leaf / "config.json"

    if sidecar_path is not None:
        try:
            sidecar = ModelSidecar.model_validate_json(sidecar_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            sidecar = _stub_sidecar(name, task)
    else:
        sidecar = _stub_sidecar(name, task)

    # Back-fill language/typeface from the linked profile when absent.
    language = sidecar.language
    typeface = sidecar.typeface
    if language is None or typeface is None:
        try:
            prof = get_profile(settings, profile)
            language = language or prof.language
            if typeface is None and prof.typeface is not None:
                typeface = prof.typeface.value
        except AppError:
            pass

    return TrainedModel(
        name=name,
        profile=profile,
        task=task,
        language=language,
        typeface=typeface,
        paths=ModelPaths(
            weights=str(weights) if weights is not None else str(leaf / f"{name}.pt"),
            sidecar=str(sidecar_path) if sidecar_path is not None else str(leaf / f"{name}.metadata.json"),
            config=str(config) if config.exists() else None,
        ),
        sidecar=sidecar,
    )


def _stub_sidecar(name: str, task: TaskEnum) -> ModelSidecar:
    """Return a minimal inferred sidecar when none is present on disk."""
    parsed = parse_model_name(name)
    return ModelSidecar(
        name=name,
        task=task.value,
        language=parsed.language,
        typeface=parsed.typeface,
        qualifier=parsed.qualifier or None,
    )


def list_models(
    settings: Settings,
    *,
    profile: str | None = None,
    task: TaskEnum | None = None,
    include_legacy: bool = True,
) -> list[TrainedModel]:
    """Walk ``shared_models_dir/*/*/*/`` and return every discovered model.

    A model's presence is a recognised weights file *or* a sidecar in the leaf
    dir (spec 08 §1) — sidecar absence is allowed.
    """
    root = settings.shared_models_dir
    if not root.is_dir():
        return []
    models: list[TrainedModel] = []
    for profile_dir in sorted(root.iterdir()):
        if not profile_dir.is_dir():
            continue
        if profile is not None and profile_dir.name != profile:
            continue
        for task_dir in sorted(profile_dir.iterdir()):
            if not task_dir.is_dir() or task_dir.name not in _TASK_SLUGS:
                continue
            task_enum = TaskEnum(task_dir.name)
            if task is not None and task_enum != task:
                continue
            for leaf in sorted(task_dir.iterdir()):
                model = _model_from_leaf(settings, leaf, profile=profile_dir.name, task=task_enum)
                if model is None:
                    continue
                if not include_legacy and parse_model_name(model.name).is_legacy:
                    continue
                models.append(model)
    models.sort(key=lambda m: m.name)
    return models


def get_model(settings: Settings, name: str) -> TrainedModel:
    """Return one model by name (404 ``model.unknown`` if absent)."""
    model = next((m for m in list_models(settings) if m.name == name), None)
    if model is None:
        raise AppError(
            code="model.unknown",
            message=f"No model named {name!r}",
            status_code=404,
        )
    return model


def has_sidecar(model: TrainedModel) -> bool:
    """True when the model's sidecar file actually exists on disk."""
    return Path(model.paths.sidecar).exists()


# ---------------------------------------------------------------------------
# sidecar regeneration (spec 08 §4)
# ---------------------------------------------------------------------------


def regenerate_sidecar(settings: Settings, name: str) -> TrainedModel:
    """Regenerate a model's sidecar from disk + the most-recent matching run.

    Walks the leaf dir, infers task + arch from ``config.json``, finds the
    newest :class:`Run` with a matching ``model_name`` and copies its
    ``args``/``trained_at``, then writes a fresh sidecar (spec 08 §4).
    """
    from pdomain_ocr_trainer_spa.domain.runs import list_runs

    model = get_model(settings, name)
    leaf = Path(model.paths.weights).parent
    config = leaf / "config.json"
    doctr_arch: str | None = None
    if config.exists():
        try:
            cfg = json.loads(config.read_text(encoding="utf-8"))
            if isinstance(cfg, dict):
                arch = cfg.get("arch") or cfg.get("doctr_arch")
                doctr_arch = str(arch) if arch is not None else None
        except (ValueError, OSError):
            doctr_arch = None

    parsed = parse_model_name(name)
    matching = [r for r in list_runs(settings) if r.model_name == name and r.kind == "train"]
    matching.sort(key=lambda r: r.started_at, reverse=True)
    args: dict[str, object] = {}
    trained_at = None
    if matching:
        run = matching[0]
        args = dict(run.args)
        trained_at = run.finished_at or run.started_at

    sidecar = ModelSidecar(
        name=name,
        task=model.task.value,
        language=model.language,
        typeface=model.typeface,
        doctr_arch=doctr_arch,
        trained_at=trained_at,
        args=args,
        qualifier=parsed.qualifier or None,
    )
    write_sidecar(settings, profile=model.profile, sidecar=sidecar)
    return get_model(settings, name)


# ---------------------------------------------------------------------------
# patch / rename / delete (spec 08 §5)
# ---------------------------------------------------------------------------


def patch_model(
    settings: Settings,
    name: str,
    *,
    language: str | None = None,
    typeface: str | None = None,
    qualifier: str | None = None,
) -> TrainedModel:
    """Update the sidecar's language/typeface/qualifier (no on-disk rename)."""
    model = get_model(settings, name)
    sidecar = model.sidecar.model_copy()
    if language is not None:
        sidecar.language = language
    if typeface is not None:
        sidecar.typeface = typeface
    if qualifier is not None:
        sidecar.qualifier = qualifier or None
    write_sidecar(settings, profile=model.profile, sidecar=sidecar)
    return get_model(settings, name)


def _model_referenced_by_active_run(settings: Settings, name: str) -> bool:
    """True when a non-terminal run references this model (spec 08 §5)."""
    from pdomain_ocr_trainer_spa.domain.runs import list_runs

    return any(r.model_name == name and r.status in {"pending", "running"} for r in list_runs(settings))


def delete_model(settings: Settings, name: str) -> None:
    """Delete a model's leaf directory (409 if a non-terminal run references it)."""
    model = get_model(settings, name)
    if _model_referenced_by_active_run(settings, name):
        raise AppError(
            code="model.in_use",
            message="Cannot delete a model referenced by an in-progress run.",
            status_code=409,
        )
    leaf = Path(model.paths.weights).parent
    shutil.rmtree(leaf, ignore_errors=True)


def rename_model(settings: Settings, name: str, new_name: str) -> TrainedModel:
    """Rename a model's leaf dir + sidecar (spec 08 §5).

    The new name must follow the new convention or be a recognised legacy
    name, and must not already exist.
    """
    model = get_model(settings, name)
    if not is_valid_model_name(new_name):
        raise AppError(
            code="model.invalid_name",
            message=(
                f"{new_name!r} is not a valid model name — use the "
                "pd-{language}-{typeface}-{task}-{date} convention."
            ),
            status_code=422,
        )
    if new_name == name:
        return model
    if next((m for m in list_models(settings) if m.name == new_name), None) is not None:
        raise AppError(
            code="model.name_taken",
            message=f"A model named {new_name!r} already exists.",
            status_code=409,
        )

    old_leaf = Path(model.paths.weights).parent
    new_leaf = old_leaf.with_name(new_name)
    old_leaf.rename(new_leaf)

    # Rename the per-file artefacts that embed the old name + rewrite sidecar.
    for child in list(new_leaf.iterdir()):
        if child.name.startswith(name):
            child.rename(new_leaf / child.name.replace(name, new_name, 1))

    sidecar = model.sidecar.model_copy(update={"name": new_name})
    write_sidecar(settings, profile=model.profile, sidecar=sidecar)
    return get_model(settings, new_name)
