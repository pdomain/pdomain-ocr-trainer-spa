"""Map a persisted run's args dict onto pdomain-ocr-training typed config models.

Torch-free: ``DetectionConfig`` / ``RecognitionConfig`` are plain pydantic
models. The full ``Run`` model lands in a later milestone; M1 accepts any
object exposing ``profile``, ``task`` and an ``args`` dict.

M12: ``TypefaceConfig`` is defined locally here (torch-free pydantic model)
because the upstream ``pdomain_ocr_training.protocols`` does not yet export it
(cross-repo gate — see plan §Cross-repo gate).  Once the upstream ships the
class, this local definition should be deleted and replaced with an import from
``pdomain_ocr_training.protocols``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from pdomain_ocr_training.protocols import DetectionConfig, RecognitionConfig
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.core.enums import TaskEnum


# ---------------------------------------------------------------------------
# TypefaceConfig — local definition (M12 cross-repo gate)
# ---------------------------------------------------------------------------


class TypefaceConfig(BaseModel):
    """Configuration for typeface-classification training (SPA-local, M12 gate).

    Reads ``<ml_training_dir>/<profile>/typeface-classification/`` as the
    dataset (image-classification/v1 layout: ``images/`` + ``metadata.jsonl``
    with a ``typeface`` column per row).

    Mirrors the Protocol surface proposed in the plan's cross-repo gate.
    Once ``pdomain_ocr_training`` ships ``TypefaceConfig``, delete this class
    and import from there.
    """

    train_path: str
    val_path: str
    arch: str = "resnet18"
    epochs: int = 20
    batch_size: int = 64
    lr: float = 1e-3
    weight_decay: float = 1e-4
    optimizer: str = "adamw"
    scheduler: str = "cosine"
    input_size: int = 64
    num_classes: int | None = None
    workers: int = 4
    amp: bool = False
    early_stop: bool = False
    early_stop_epochs: int = 5
    early_stop_delta: float = 0.001
    output_dir: str = Field(default=".")
    device: int | None = None
    pretrained: bool = True
    name: str | None = None


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
_TYPEFACE_FIELDS = frozenset(TypefaceConfig.model_fields)


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


def build_typeface_config(run: RunLike) -> TypefaceConfig:
    """Build a torch-free TypefaceConfig from the run's args dict.

    The caller is responsible for supplying ``train_path`` and ``val_path``
    in ``run.args``; ``prepare_worker_args`` in ``domain/runs.py`` fills those
    from settings for the ``typeface-classification`` task.
    """
    args = run.args
    payload = _selected(args, _TYPEFACE_FIELDS)
    payload.setdefault("train_path", str(args.get("train_path", "")))
    payload.setdefault("val_path", str(args.get("val_path", "")))
    payload.setdefault("output_dir", str(args.get("output_dir", ".")))
    return TypefaceConfig.model_validate(payload)
