"""Domain-layer tests for per-profile training-config defaults (spec 04 §3)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from pdomain_ocr_trainer_spa.core.enums import TaskEnum
from pdomain_ocr_trainer_spa.core.errors import AppError
from pdomain_ocr_trainer_spa.domain import training_defaults as td

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.settings import Settings


def test_detection_seed_matches_spec_04_section_3_2() -> None:
    seed = td.seed_defaults(TaskEnum.detection)
    assert seed == {
        "arch": "db_resnet50",
        "epochs": 100,
        "batch_size": 2,
        "workers": 4,
        "lr": 0.002,
        "weight_decay": 0.0,
        "optimizer": "adam",
        "scheduler": "poly",
        "input_size": 1024,
        "rotation": False,
        "amp": False,
        "pretrained": True,
        "early_stop": False,
        "early_stop_epochs": 5,
        "early_stop_delta": 0.01,
    }


def test_recognition_seed_matches_spec_04_section_3_2() -> None:
    seed = td.seed_defaults(TaskEnum.recognition)
    assert seed["arch"] == "crnn_vgg16_bn"
    assert seed["epochs"] == 10
    assert seed["batch_size"] == 64
    assert seed["scheduler"] == "cosine"
    assert seed["vocab_library"] == ["french"]
    assert "custom_characters" in seed


def test_seed_is_a_fresh_copy() -> None:
    a = td.seed_defaults(TaskEnum.detection)
    a["epochs"] = 999
    b = td.seed_defaults(TaskEnum.detection)
    assert b["epochs"] == 100


def test_seed_rejects_classifier_task() -> None:
    with pytest.raises(AppError) as excinfo:
        td.seed_defaults(TaskEnum.glyph_classification)
    assert excinfo.value.code == "training_defaults.task_unsupported"
    assert excinfo.value.status_code == 422


def test_get_unset_raises_404(settings: Settings) -> None:
    with pytest.raises(AppError) as excinfo:
        td.get_training_defaults(settings, profile="all", task=TaskEnum.detection)
    assert excinfo.value.code == "training_defaults.not_set"
    assert excinfo.value.status_code == 404


def test_set_then_get_round_trips_recognition(settings: Settings) -> None:
    args = {**td.seed_defaults(TaskEnum.recognition), "epochs": 50}
    td.set_training_defaults(settings, profile="all", task=TaskEnum.recognition, args=args)
    got = td.get_training_defaults(settings, profile="all", task=TaskEnum.recognition)
    assert got["epochs"] == 50


def test_set_then_get_round_trips_detection(settings: Settings) -> None:
    args = {**td.seed_defaults(TaskEnum.detection), "batch_size": 8}
    td.set_training_defaults(settings, profile="all", task=TaskEnum.detection, args=args)
    got = td.get_training_defaults(settings, profile="all", task=TaskEnum.detection)
    assert got["batch_size"] == 8


def test_detection_and_recognition_defaults_are_independent(
    settings: Settings,
) -> None:
    td.set_training_defaults(
        settings,
        profile="all",
        task=TaskEnum.detection,
        args={"epochs": 7},
    )
    td.set_training_defaults(
        settings,
        profile="all",
        task=TaskEnum.recognition,
        args={"epochs": 9},
    )
    assert td.get_training_defaults(settings, profile="all", task=TaskEnum.detection)["epochs"] == 7
    assert td.get_training_defaults(settings, profile="all", task=TaskEnum.recognition)["epochs"] == 9
    # Both stored in one training_defaults.json keyed by task.
    path = settings.app_data_root / "profiles" / "all" / "training_defaults.json"
    assert set(json.loads(path.read_text())) == {"detection", "recognition"}


def test_delete_falls_back_to_unset(settings: Settings) -> None:
    td.set_training_defaults(settings, profile="all", task=TaskEnum.detection, args={"epochs": 7})
    td.delete_training_defaults(settings, profile="all", task=TaskEnum.detection)
    with pytest.raises(AppError) as excinfo:
        td.get_training_defaults(settings, profile="all", task=TaskEnum.detection)
    assert excinfo.value.code == "training_defaults.not_set"


def test_delete_last_task_removes_the_file(settings: Settings) -> None:
    td.set_training_defaults(settings, profile="all", task=TaskEnum.detection, args={"epochs": 7})
    td.delete_training_defaults(settings, profile="all", task=TaskEnum.detection)
    path = settings.app_data_root / "profiles" / "all" / "training_defaults.json"
    assert not path.exists()


def test_delete_unset_task_is_a_noop(settings: Settings) -> None:
    # Must not raise even though nothing was saved.
    td.delete_training_defaults(settings, profile="all", task=TaskEnum.recognition)
