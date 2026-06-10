"""config_build tests — Run.args -> torch-free typed config models.

Covers DetectionConfig, RecognitionConfig, and TypefaceConfig builders.
"""

from __future__ import annotations

from pdomain_ocr_trainer_spa.core.enums import TaskEnum
from pdomain_ocr_trainer_spa.training.config_build import (
    build_detection_config,
    build_recognition_config,
    build_typeface_config,
)


class _Run:
    def __init__(self, task: TaskEnum, args: dict[str, object]) -> None:
        self.profile = "all"
        self.task = task
        self.args = args


def test_build_detection_config_maps_args() -> None:
    run = _Run(
        TaskEnum.detection,
        {"train_path": "/t", "val_path": "/v", "epochs": 50, "rotation": True},
    )
    cfg = build_detection_config(run)
    assert str(cfg.train_path) == "/t"
    assert str(cfg.val_path) == "/v"
    assert cfg.epochs == 50
    assert cfg.rotation is True


def test_build_detection_config_uses_defaults() -> None:
    cfg = build_detection_config(_Run(TaskEnum.detection, {"train_path": "/t", "val_path": "/v"}))
    assert cfg.arch == "db_resnet50"
    assert cfg.input_size == 1024


def test_build_recognition_config_resolves_named_vocab() -> None:
    run = _Run(TaskEnum.recognition, {"train_path": "/t", "val_path": "/v", "vocab": "english"})
    cfg = build_recognition_config(run)
    assert cfg.vocab == "english"


def test_build_recognition_config_resolves_custom_vocab() -> None:
    run = _Run(
        TaskEnum.recognition,
        {"train_path": "/t", "val_path": "/v", "vocab_library": "custom", "custom_characters": "abc"},
    )
    cfg = build_recognition_config(run)
    assert cfg.vocab == "CUSTOM:abc"


def test_build_recognition_config_custom_characters_implies_custom() -> None:
    run = _Run(
        TaskEnum.recognition,
        {"train_path": "/t", "val_path": "/v", "custom_characters": "xyz"},
    )
    assert build_recognition_config(run).vocab == "CUSTOM:xyz"


# ---------------------------------------------------------------------------
# TypefaceConfig tests (M12)
# ---------------------------------------------------------------------------


class _RunView:
    def __init__(self) -> None:
        self.profile = "clogaelach"
        self.task = TaskEnum.typeface_classification
        self.args: dict[str, object] = {
            "train_path": "/ml-training/clogaelach/typeface-classification",
            "val_path": "/ml-validation/clogaelach/typeface-classification",
            "output_dir": "/runs/123",
            "epochs": 15,
        }


def test_build_typeface_config_basic() -> None:
    view = _RunView()
    cfg = build_typeface_config(view)
    assert str(cfg.train_path) == "/ml-training/clogaelach/typeface-classification"
    assert str(cfg.val_path) == "/ml-validation/clogaelach/typeface-classification"
    assert cfg.epochs == 15


def test_build_typeface_config_defaults() -> None:
    view = _RunView()
    view.args = {
        "train_path": "/ml-training/clogaelach/typeface-classification",
        "val_path": "/ml-validation/clogaelach/typeface-classification",
        "output_dir": "/runs/123",
    }
    cfg = build_typeface_config(view)
    assert cfg.epochs == 20  # TypefaceConfig default
    assert cfg.arch == "resnet18"  # TypefaceConfig default
