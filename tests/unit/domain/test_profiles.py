"""Domain-layer tests for profile discovery + CRUD (spec 04 §6)."""

from __future__ import annotations

import json
import tomllib
from typing import TYPE_CHECKING

import pytest

from pdomain_ocr_trainer_spa.core.enums import TypefaceEnum
from pdomain_ocr_trainer_spa.core.errors import AppError
from pdomain_ocr_trainer_spa.domain import profiles as dom

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.settings import Settings


def _toml(settings: Settings, split: str, name: str) -> dict[str, object]:
    root = settings.ml_training_dir if split == "train" else settings.ml_validation_dir
    path = root / name / "profile.toml"
    return tomllib.loads(path.read_text()) if path.exists() else {}


def _seed_recognition(settings: Settings, split: str, name: str, crops: int) -> None:
    root = settings.ml_training_dir if split == "train" else settings.ml_validation_dir
    task = root / name / "recognition"
    task.mkdir(parents=True, exist_ok=True)
    labels = {f"crop_{i}.png": f"text {i}" for i in range(crops)}
    (task / "labels.json").write_text(json.dumps(labels))


def test_normalize_profile_name() -> None:
    assert dom.normalize_profile_name("Cló Gaelach") == "cló-gaelach"
    assert dom.normalize_profile_name("base-ocr") == "all"
    assert dom.normalize_profile_name("") == "all"
    assert dom.normalize_profile_name("Italics_Set") == "italics-set"


def test_scenario_1_fresh_install_has_only_all(settings: Settings) -> None:
    result = dom.list_profiles(settings)
    assert [p.name for p in result] == ["all"]
    only = result[0]
    assert only.is_base is True
    assert only.counts.recognition_train_crops == 0
    assert only.has_training_data is False


def test_scenario_3_create_writes_both_toml_files(settings: Settings) -> None:
    profile = dom.create_profile(
        settings,
        name="Clogaelach",
        language="ga",
        typeface=TypefaceEnum.clogaelach,
    )
    assert profile.name == "clogaelach"
    assert profile.language == "ga"
    assert profile.typeface == TypefaceEnum.clogaelach
    train = _toml(settings, "train", "clogaelach")
    val = _toml(settings, "val", "clogaelach")
    assert train == val
    assert train["language"] == "ga"
    assert train["typeface"] == "clogaelach"


def test_create_without_metadata_writes_no_toml(settings: Settings) -> None:
    dom.create_profile(settings, name="plain")
    assert _toml(settings, "train", "plain") == {}
    assert _toml(settings, "val", "plain") == {}


def test_create_duplicate_is_409(settings: Settings) -> None:
    dom.create_profile(settings, name="dup")
    with pytest.raises(AppError) as exc:
        dom.create_profile(settings, name="dup")
    assert exc.value.status_code == 409


def test_scenario_4_clear_fields_progressively(settings: Settings) -> None:
    dom.create_profile(settings, name="clogaelach", language="ga", typeface=TypefaceEnum.clogaelach)
    dom.update_profile(settings, "clogaelach", fields={"typeface": None})
    train = _toml(settings, "train", "clogaelach")
    assert train.get("language") == "ga"
    assert "typeface" not in train
    assert _toml(settings, "train", "clogaelach") == _toml(settings, "val", "clogaelach")

    dom.update_profile(settings, "clogaelach", fields={"language": None})
    assert _toml(settings, "train", "clogaelach") == {}
    assert _toml(settings, "val", "clogaelach") == {}


def test_update_display_name(settings: Settings) -> None:
    dom.create_profile(settings, name="clogaelach")
    updated = dom.update_profile(settings, "clogaelach", fields={"display_name": "Cló Gaelach"})
    assert updated.display_name == "Cló Gaelach"


def test_update_unknown_profile_is_404(settings: Settings) -> None:
    with pytest.raises(AppError) as exc:
        dom.update_profile(settings, "ghost", fields={"language": "en"})
    assert exc.value.status_code == 404


def test_scenario_6_delete_removes_dataset_dirs(settings: Settings) -> None:
    dom.create_profile(settings, name="clogaelach")
    shared_root = settings.shared_models_dir
    shared_root.mkdir(parents=True, exist_ok=True)
    (shared_root / "unrelated.txt").write_text("other profile artefact")

    dom.delete_profile(settings, "clogaelach")

    assert not (settings.ml_training_dir / "clogaelach").exists()
    assert not (settings.ml_validation_dir / "clogaelach").exists()
    assert (shared_root / "unrelated.txt").exists()


def test_delete_all_profile_is_409(settings: Settings) -> None:
    with pytest.raises(AppError) as exc:
        dom.delete_profile(settings, "all")
    assert exc.value.status_code == 409
    assert exc.value.code == "profile.is_base"


def test_delete_profile_with_data_is_409(settings: Settings) -> None:
    dom.create_profile(settings, name="hasdata")
    _seed_recognition(settings, "train", "hasdata", crops=3)
    with pytest.raises(AppError) as exc:
        dom.delete_profile(settings, "hasdata")
    assert exc.value.status_code == 409
    assert exc.value.code == "profile.has_data"


def test_counts_reflect_recognition_labels(settings: Settings) -> None:
    dom.create_profile(settings, name="counted")
    _seed_recognition(settings, "train", "counted", crops=5)
    _seed_recognition(settings, "val", "counted", crops=2)
    profile = dom.get_profile(settings, "counted")
    assert profile.counts.recognition_train_crops == 5
    assert profile.counts.recognition_val_crops == 2
    assert profile.has_training_data is True
    assert profile.has_validation_data is True


def test_toml_conflict_is_409(settings: Settings) -> None:
    dom.create_profile(settings, name="conflict", language="en")
    val_toml = settings.ml_validation_dir / "conflict" / "profile.toml"
    val_toml.write_text('language = "fr"\n')
    with pytest.raises(AppError) as exc:
        dom.get_profile(settings, "conflict")
    assert exc.value.code == "profile.toml.conflict"


def test_legacy_layout_detection_and_migration(settings: Settings) -> None:
    flat = settings.ml_training_dir / "detection"
    flat.mkdir(parents=True)
    (flat / "labels.json").write_text("{}")
    assert dom.has_legacy_layout(settings) is True

    dom.migrate_legacy(settings)
    assert (settings.ml_training_dir / "all" / "detection" / "labels.json").exists()
    assert dom.has_legacy_layout(settings) is False
