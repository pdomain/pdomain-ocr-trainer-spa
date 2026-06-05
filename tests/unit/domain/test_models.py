"""Unit tests for domain/models.py — the model registry domain logic (spec 08)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from pdomain_ocr_trainer_spa.core.enums import TaskEnum, TypefaceEnum
from pdomain_ocr_trainer_spa.core.errors import AppError
from pdomain_ocr_trainer_spa.core.models import ModelSidecar
from pdomain_ocr_trainer_spa.domain import models as dom
from pdomain_ocr_trainer_spa.domain.profiles import create_profile

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.settings import Settings


# --- model-name parsing (spec 08 §2) -------------------------------------


def test_parse_new_form_name() -> None:
    """A new-convention name yields language + typeface, is_legacy False."""
    parsed = dom.parse_model_name("pd-ga-clogaelach-recognition-2026-05-05")
    assert parsed.language == "ga"
    assert parsed.typeface == "clogaelach"
    assert parsed.task == "recognition"
    assert parsed.is_legacy is False


def test_parse_new_form_name_with_qualifier() -> None:
    """The qualifier slot captures everything after the date."""
    parsed = dom.parse_model_name("pd-en-roman-detection-2026-05-05-finetuned")
    assert parsed.qualifier == "2026-05-05-finetuned"
    assert parsed.is_legacy is False


def test_parse_legacy_name() -> None:
    """A legacy name has a profile and no language/typeface."""
    parsed = dom.parse_model_name("pd-clogaelach-recognition-model-finetuned-2026")
    assert parsed.is_legacy is True
    assert parsed.profile == "clogaelach"
    assert parsed.task == "recognition"
    assert parsed.language is None


def test_is_valid_model_name() -> None:
    """Names without a recognised task token are invalid."""
    assert dom.is_valid_model_name("pd-ga-clogaelach-recognition-2026-05-05")
    assert dom.is_valid_model_name("pd-clogaelach-detection-old")
    assert not dom.is_valid_model_name("totally-free-form")


# --- discovery (spec 08 §1) ----------------------------------------------


def _write_model(
    settings: Settings,
    *,
    profile: str,
    task: str,
    name: str,
    sidecar: bool = True,
    weights: bool = True,
) -> None:
    leaf = settings.shared_models_dir / profile / task / name
    leaf.mkdir(parents=True, exist_ok=True)
    if weights:
        (leaf / "model.pt").write_bytes(b"\x00")
    if sidecar:
        (leaf / f"{name}.metadata.json").write_text(ModelSidecar(name=name, task=task).model_dump_json())


def test_list_models_discovers_weights_only_dir(settings: Settings) -> None:
    """A leaf dir with weights but no sidecar is still discovered (spec 08 §1)."""
    _write_model(
        settings,
        profile="clogaelach",
        task="recognition",
        name="pd-ga-clogaelach-recognition-2026-05-05",
        sidecar=False,
    )
    models = dom.list_models(settings)
    assert len(models) == 1
    assert dom.has_sidecar(models[0]) is False


def test_list_models_filters(settings: Settings) -> None:
    """profile / task / include_legacy filters narrow the result set."""
    _write_model(
        settings,
        profile="clogaelach",
        task="recognition",
        name="pd-ga-clogaelach-recognition-2026-05-05",
    )
    _write_model(
        settings,
        profile="clogaelach",
        task="detection",
        name="pd-clogaelach-detection-legacy",
    )
    assert len(dom.list_models(settings, task=TaskEnum.recognition)) == 1
    assert len(dom.list_models(settings, include_legacy=False)) == 1


def test_get_model_unknown_raises_404(settings: Settings) -> None:
    """A missing model raises AppError(404)."""
    with pytest.raises(AppError) as exc:
        dom.get_model(settings, "nope")
    assert exc.value.status_code == 404


# --- regenerate / patch / rename / delete (spec 08 §4-5) -----------------


def test_regenerate_sidecar_recreates_missing_file(settings: Settings) -> None:
    """regenerate_sidecar writes a fresh sidecar for a weights-only model."""
    name = "pd-ga-clogaelach-recognition-2026-05-05"
    _write_model(
        settings,
        profile="clogaelach",
        task="recognition",
        name=name,
        sidecar=False,
    )
    model = dom.regenerate_sidecar(settings, name)
    assert dom.has_sidecar(model)


def test_patch_model_updates_sidecar(settings: Settings) -> None:
    """patch_model updates language/typeface in the sidecar."""
    name = "pd-clogaelach-recognition-legacy"
    _write_model(settings, profile="clogaelach", task="recognition", name=name)
    model = dom.patch_model(settings, name, language="ga", typeface="clogaelach")
    assert model.sidecar.language == "ga"
    assert model.sidecar.typeface == "clogaelach"


def test_rename_model_moves_dir_and_sidecar(settings: Settings) -> None:
    """rename_model relocates the leaf dir and rewrites the sidecar name."""
    old = "pd-clogaelach-recognition-legacy"
    new = "pd-ga-clogaelach-recognition-2026-05-05"
    _write_model(settings, profile="clogaelach", task="recognition", name=old)
    model = dom.rename_model(settings, old, new)
    assert model.name == new
    assert not (settings.shared_models_dir / "clogaelach" / "recognition" / old).exists()
    with pytest.raises(AppError):
        dom.get_model(settings, old)


def test_rename_rejects_invalid_name(settings: Settings) -> None:
    """rename_model rejects a free-form target name (422)."""
    name = "pd-clogaelach-recognition-legacy"
    _write_model(settings, profile="clogaelach", task="recognition", name=name)
    with pytest.raises(AppError) as exc:
        dom.rename_model(settings, name, "free-form")
    assert exc.value.status_code == 422


def test_rename_rejects_name_collision(settings: Settings) -> None:
    """rename_model refuses an already-taken name (409)."""
    a = "pd-clogaelach-recognition-a"
    b = "pd-ga-clogaelach-recognition-2026-05-05"
    _write_model(settings, profile="clogaelach", task="recognition", name=a)
    _write_model(settings, profile="clogaelach", task="recognition", name=b)
    with pytest.raises(AppError) as exc:
        dom.rename_model(settings, a, b)
    assert exc.value.status_code == 409


def test_delete_model_removes_leaf(settings: Settings) -> None:
    """delete_model removes the leaf directory."""
    name = "pd-ga-clogaelach-recognition-2026-05-05"
    _write_model(settings, profile="clogaelach", task="recognition", name=name)
    dom.delete_model(settings, name)
    with pytest.raises(AppError):
        dom.get_model(settings, name)


def test_backfill_language_from_profile(settings: Settings) -> None:
    """A legacy model with no sidecar slots back-fills lang/typeface from profile."""
    create_profile(
        settings,
        name="clogaelach",
        language="ga",
        typeface=TypefaceEnum.clogaelach,
    )
    name = "pd-clogaelach-recognition-legacy"
    leaf = settings.shared_models_dir / "clogaelach" / "recognition" / name
    leaf.mkdir(parents=True, exist_ok=True)
    (leaf / "model.pt").write_bytes(b"\x00")
    (leaf / f"{name}.metadata.json").write_text(json.dumps({"name": name, "task": "recognition"}))
    model = dom.get_model(settings, name)
    assert model.language == "ga"
    assert model.typeface == "clogaelach"
