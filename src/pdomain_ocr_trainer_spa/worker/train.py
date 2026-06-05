"""Training-worker subprocess entry point (spec 02-backend §5, spec 06 §3).

Invoked as::

    python -m pdomain_ocr_trainer_spa.worker.train --run-dir runs/<id>

The worker:

1. Reads ``runs/<id>/{manifest,args}.json``.
2. Builds the typed config via ``training/config_build.py``.
3. Sets dataset-dir / HF / CUDA env vars from the manifest.
4. Instantiates ``pdomain_ocr_training.LocalTrainingRunner`` and **fully drains**
   ``train_detection`` / ``train_recognition`` — abandoning the iterator
   strands the in-process training thread and the GPU.
5. Emits one ``@@PDEVENT@@ {json}`` stdout line per ``TrainingEvent``,
   mirrors ``message`` to ``runs/<id>/stdout.log``, lets stderr flow to
   ``runs/<id>/stderr.log``.
6. Exits ``0`` after the ``done`` event, non-zero after ``error``.

``torch`` / DocTR are imported **only** here (via ``LocalTrainingRunner``),
never in the FastAPI web process. The ``--runner`` flag lets tests inject a
torch-free fake runner; production always uses ``LocalTrainingRunner``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pdomain_ocr_training.protocols import DetectionConfig, RecognitionConfig

EVENT_PREFIX = "@@PDEVENT@@"


class _TrainingRunner(Protocol):
    """The minimal ``ITrainingRunner`` surface the worker drives.

    ``LocalTrainingRunner`` satisfies this; tests inject a torch-free fake.
    Each ``train_*`` method yields ``TrainingEvent``-shaped objects. The
    config models are torch-free pydantic models (D-T1).
    """

    def train_detection(self, profile: str, config: DetectionConfig) -> Iterator[object]: ...

    def train_recognition(self, profile: str, config: RecognitionConfig) -> Iterator[object]: ...


def emit_event(event: dict[str, object], *, stdout_log: Path | None = None) -> None:
    """Write one ``@@PDEVENT@@`` line to stdout and mirror ``message`` to the log."""
    sys.stdout.write(f"{EVENT_PREFIX} {json.dumps(event)}\n")
    sys.stdout.flush()
    if stdout_log is not None:
        message = str(event.get("message", ""))
        if message:
            with stdout_log.open("a", encoding="utf-8") as fh:
                fh.write(message + "\n")


def _apply_env(manifest: dict[str, object], args: dict[str, object]) -> None:
    """Set process env from the run manifest + resolved args (dirs, CUDA device)."""
    train_path = args.get("train_path")
    val_path = args.get("val_path")
    if isinstance(train_path, str):
        train_root = str(Path(train_path).parent.parent)
        os.environ["PD_OCR_TRAINER_ML_TRAINING_DIR"] = train_root
    if isinstance(val_path, str):
        val_root = str(Path(val_path).parent.parent)
        os.environ["PD_OCR_TRAINER_ML_VALIDATION_DIR"] = val_root
    device = manifest.get("device")
    if isinstance(device, int):
        os.environ["CUDA_VISIBLE_DEVICES"] = str(device)


def _build_runner() -> _TrainingRunner:
    """Instantiate the real ``LocalTrainingRunner`` (imports torch / DocTR)."""
    from pdomain_ocr_training import LocalTrainingRunner

    return LocalTrainingRunner()


def _iter_events(
    runner: _TrainingRunner, *, task: str, profile: str, args: dict[str, object]
) -> Iterator[object]:
    """Drive the runner's ``train_*`` generator for the given task."""
    from pdomain_ocr_trainer_spa.core.enums import TaskEnum
    from pdomain_ocr_trainer_spa.training.config_build import (
        build_detection_config,
        build_recognition_config,
    )

    class _RunView:
        def __init__(self) -> None:
            self.profile = profile
            self.task = TaskEnum(task)
            self.args = args

    view = _RunView()
    if task == "detection":
        det_cfg = build_detection_config(view)
        return runner.train_detection(profile, det_cfg)
    rec_cfg = build_recognition_config(view)
    return runner.train_recognition(profile, rec_cfg)


def run_worker(run_dir: Path, *, runner: _TrainingRunner | None = None) -> int:
    """Execute one training run; returns the process exit code.

    ``runner`` is injectable so tests can pass a torch-free fake; production
    leaves it ``None`` and the real ``LocalTrainingRunner`` is built.
    """
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    args = json.loads((run_dir / "args.json").read_text(encoding="utf-8"))
    stdout_log = run_dir / "stdout.log"

    _apply_env(manifest, args)

    task = str(manifest.get("task", ""))
    profile = str(manifest.get("profile", ""))

    if runner is None:
        runner = _build_runner()

    exit_code = 0
    saw_done = False
    try:
        for event in _iter_events(runner, task=task, profile=profile, args=args):
            payload = _event_to_dict(event)
            emit_event(payload, stdout_log=stdout_log)
            if payload.get("kind") == "error":
                exit_code = 1
            elif payload.get("kind") == "done":
                saw_done = True
    except Exception as exc:  # noqa: BLE001 — surface any worker crash as an error event
        emit_event(
            {
                "kind": "error",
                "message": f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
            },
            stdout_log=stdout_log,
        )
        return 1

    # A successful run writes its model sidecar so /models can discover it.
    if exit_code == 0 and saw_done:
        try:
            write_model_sidecar(manifest, args)
        except OSError as exc:
            emit_event(
                {"kind": "log", "message": f"sidecar write failed: {exc}"},
                stdout_log=stdout_log,
            )
    return exit_code


def write_model_sidecar(manifest: dict[str, object], args: dict[str, object]) -> Path | None:
    """Write ``<model_name>.metadata.json`` under the run's shared-models dir.

    The sidecar shape matches :class:`~pdomain_ocr_trainer_spa.core.models.ModelSidecar`
    (spec 08 §3). Returns the sidecar path, or None when no ``shared_models_dir``
    arg was supplied.
    """
    shared = args.get("shared_models_dir")
    name = str(manifest.get("model_name", "") or args.get("name", ""))
    if not isinstance(shared, str) or not name:
        return None
    leaf = Path(shared) / name
    leaf.mkdir(parents=True, exist_ok=True)
    sidecar: dict[str, object] = {
        "name": name,
        "task": str(manifest.get("task", "")),
        "language": None,
        "typeface": None,
        "doctr_arch": None,
        "trainer_version": None,
        "trained_at": datetime.now(UTC).isoformat(),
        "trained_on": [],
        "args": args,
        "qualifier": None,
        "eval": None,
    }
    sidecar_path = leaf / f"{name}.metadata.json"
    sidecar_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    return sidecar_path


def _event_to_dict(event: object) -> dict[str, object]:
    """Normalize a ``TrainingEvent`` (or dict) into a plain JSON-able dict."""
    if isinstance(event, dict):
        return event
    dump = getattr(event, "model_dump", None)
    if callable(dump):
        result: object = dump()
        if isinstance(result, dict):
            return result
    return {"kind": "log", "message": str(event)}


def main(argv: list[str] | None = None) -> int:
    """CLI entry point — parse ``--run-dir`` and execute the run."""
    parser = argparse.ArgumentParser(prog="pdomain_ocr_trainer_spa.worker.train")
    parser.add_argument("--run-dir", required=True, type=Path)
    ns = parser.parse_args(argv)
    return run_worker(ns.run_dir)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
