"""Per-profile training-config defaults (spec 04 §3).

The training-defaults are *advisory*: they pre-fill the run-creation form for
a ``(profile, task)`` pair and nothing else reads them. They live at
``<app_data_root>/profiles/<name>/training_defaults.json`` as a flat
``{task: args-dict}`` map. When a task has never been edited the GET endpoint
404s and the SPA falls back to the seed (the ``pdomain-ocr-training`` config-model
defaults — spec 04 §3.2, mirrored verbatim below).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pdomain_ocr_trainer_spa.core.enums import TaskEnum
from pdomain_ocr_trainer_spa.core.errors import AppError
from pdomain_ocr_trainer_spa.domain.profiles import normalize_profile_name

if TYPE_CHECKING:
    from pathlib import Path

    from pdomain_ocr_trainer_spa.settings import Settings

# Seed defaults — verbatim from spec 04 §3.2 (the pdomain-ocr-training
# DetectionConfig / RecognitionConfig defaults, protocols.py:85-188). A test
# pins these field-for-field.
_DETECTION_SEED: dict[str, object] = {
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

_RECOGNITION_SEED: dict[str, object] = {
    "arch": "crnn_vgg16_bn",
    "epochs": 10,
    "batch_size": 64,
    "workers": 4,
    "lr": 0.001,
    "weight_decay": 0.0,
    "optimizer": "adam",
    "scheduler": "cosine",
    "input_size": 32,
    "amp": False,
    "pretrained": True,
    "early_stop": False,
    "early_stop_epochs": 5,
    "early_stop_delta": 0.01,
    "vocab_library": ["french"],
    "custom_characters": "",
}

_SEEDS: dict[TaskEnum, dict[str, object]] = {
    TaskEnum.detection: _DETECTION_SEED,
    TaskEnum.recognition: _RECOGNITION_SEED,
}


def seed_defaults(task: TaskEnum) -> dict[str, object]:
    """Return a fresh copy of the seed training-args for a task.

    Raises ``422 training_defaults.task_unsupported`` for the classifier tasks
    whose config models are still a future ``pdomain-ocr-training`` addition.
    """
    seed = _SEEDS.get(task)
    if seed is None:
        raise AppError(
            code="training_defaults.task_unsupported",
            message=f"No training-config seed for task {task.value!r}",
            status_code=422,
        )
    return json.loads(json.dumps(seed))  # deep copy


def _defaults_path(settings: Settings, profile: str) -> Path:
    """Path to a profile's ``training_defaults.json`` under the app-data root."""
    return settings.app_data_root / "profiles" / profile / "training_defaults.json"


def _read_all(settings: Settings, profile: str) -> dict[str, dict[str, object]]:
    """Read the whole ``{task: args}`` map for a profile; missing -> empty."""
    path = _defaults_path(settings, profile)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        str(k): v for k, v in data.items() if isinstance(v, dict)
    }


def _write_all(
    settings: Settings, profile: str, data: dict[str, dict[str, object]]
) -> None:
    """Write (or delete) a profile's ``training_defaults.json`` — empty payload removes it."""
    path = _defaults_path(settings, profile)
    if not data:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_training_defaults(
    settings: Settings, *, profile: str, task: TaskEnum
) -> dict[str, object]:
    """Return a profile's saved training-defaults for a task.

    Raises ``404 training_defaults.not_set`` when the task has never been
    edited — the SPA then falls back to :func:`seed_defaults` (spec 04 §3.3).
    """
    seed_defaults(task)  # validates the task is supported
    normalized = normalize_profile_name(profile)
    saved = _read_all(settings, normalized).get(task.value)
    if saved is None:
        raise AppError(
            code="training_defaults.not_set",
            message=f"No training-defaults for {normalized!r} / {task.value}",
            status_code=404,
        )
    return saved


def set_training_defaults(
    settings: Settings, *, profile: str, task: TaskEnum, args: dict[str, object]
) -> dict[str, object]:
    """Persist a profile's training-defaults for a task and return the stored args."""
    seed_defaults(task)  # validates the task is supported
    normalized = normalize_profile_name(profile)
    data = _read_all(settings, normalized)
    data[task.value] = args
    _write_all(settings, normalized, data)
    return args


def delete_training_defaults(
    settings: Settings, *, profile: str, task: TaskEnum
) -> None:
    """Drop a profile's training-defaults for a task (falls back to seed thereafter)."""
    seed_defaults(task)  # validates the task is supported
    normalized = normalize_profile_name(profile)
    data = _read_all(settings, normalized)
    data.pop(task.value, None)
    _write_all(settings, normalized, data)
