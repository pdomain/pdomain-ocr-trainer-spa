"""Map a persisted run's args dict onto pdomain-ocr-training typed config models.

Torch-free: ``DetectionConfig`` / ``RecognitionConfig`` are plain pydantic
models. The full ``Run`` model lands in a later milestone; M1 accepts any
object exposing ``profile``, ``task`` and an ``args`` dict.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from pdomain_ocr_training.protocols import DetectionConfig, RecognitionConfig

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.core.enums import TaskEnum


class RunLike(Protocol):
    """The minimal run surface ``config_build`` reads."""

    profile: str
    task: TaskEnum
    args: dict[str, object]


def _resolve_vocab(args: dict[str, object]) -> str:
    """Resolve vocab_library + custom_characters into a final vocab string."""
    library = args.get("vocab_library")
    if library == "custom" or args.get("custom_characters"):
        chars = str(args.get("custom_characters", ""))
        return f"CUSTOM:{chars}"
    if isinstance(library, str) and library:
        return library
    return str(args.get("vocab", "french"))


_DETECTION_FIELDS = frozenset(DetectionConfig.model_fields)
_RECOGNITION_FIELDS = frozenset(RecognitionConfig.model_fields)


def _selected(args: dict[str, object], fields: frozenset[str]) -> dict[str, object]:
    """Return the subset of ``args`` that maps onto known config fields."""
    return {k: v for k, v in args.items() if k in fields}


def build_detection_config(run: RunLike) -> DetectionConfig:
    """Build a torch-free DetectionConfig from the run's args dict."""
    args = run.args
    payload = _selected(args, _DETECTION_FIELDS)
    payload.setdefault("train_path", str(args.get("train_path", "")))
    payload.setdefault("val_path", str(args.get("val_path", "")))
    payload.setdefault("output_dir", str(args.get("output_dir", ".")))
    return DetectionConfig.model_validate(payload)


def build_recognition_config(run: RunLike) -> RecognitionConfig:
    """Build a torch-free RecognitionConfig from the run's args dict."""
    args = run.args
    payload = _selected(args, _RECOGNITION_FIELDS)
    payload.setdefault("train_path", str(args.get("train_path", "")))
    payload.setdefault("val_path", str(args.get("val_path", "")))
    payload.setdefault("output_dir", str(args.get("output_dir", ".")))
    payload["vocab"] = _resolve_vocab(args)
    return RecognitionConfig.model_validate(payload)
