"""Unit tests for worker/train.py — torch-free, with an injected fake runner.

The worker drives ``pd_ocr_training``'s ``ITrainingRunner``; here we inject a
fake runner whose ``train_*`` methods yield plain dicts, so no torch / DocTR /
GPU is touched (spec 14-testing §5.2).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pd_ocr_trainer_spa.worker import train as worker

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class _FakeRunner:
    """Torch-free stand-in for LocalTrainingRunner — yields scripted events."""

    def __init__(self, events: list[dict[str, object]]) -> None:
        self._events = events

    def train_recognition(
        self, profile: str, config: object
    ) -> Iterator[dict[str, object]]:
        del profile, config
        yield from self._events

    def train_detection(
        self, profile: str, config: object
    ) -> Iterator[dict[str, object]]:
        del profile, config
        yield from self._events


def _write_run_dir(run_dir: Path, *, task: str = "recognition") -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": "run-1",
        "profile": "clogaelach",
        "task": task,
        "model_name": "pd-ga-clogaelach-recognition-2026-05-21",
        "args": {},
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (run_dir / "args.json").write_text(
        json.dumps(
            {
                "epochs": 2,
                "train_path": "/tmp/ml-training/clogaelach/recognition",
                "val_path": "/tmp/ml-validation/clogaelach/recognition",
                "output_dir": str(run_dir / "artefacts"),
                "vocab": "french",
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "stdout.log").touch()


def test_run_worker_emits_pdevent_lines(tmp_path: Path, capsys) -> None:
    """Each TrainingEvent becomes one @@PDEVENT@@ stdout line."""
    run_dir = tmp_path / "runs" / "run-1"
    _write_run_dir(run_dir)
    runner = _FakeRunner(
        [
            {"kind": "epoch", "message": "epoch 1/2", "progress": 0.5, "data": {}},
            {"kind": "epoch", "message": "epoch 2/2", "progress": 1.0, "data": {}},
            {"kind": "done", "message": "Training completed successfully."},
        ]
    )
    code = worker.run_worker(run_dir, runner=runner)
    assert code == 0

    out_lines = [
        ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("@@PDEVENT@@")
    ]
    assert len(out_lines) == 3
    first = json.loads(out_lines[0][len("@@PDEVENT@@") :])
    assert first["kind"] == "epoch"


def test_run_worker_mirrors_messages_to_stdout_log(tmp_path: Path) -> None:
    """Human-readable event messages are mirrored to stdout.log."""
    run_dir = tmp_path / "runs" / "run-1"
    _write_run_dir(run_dir)
    runner = _FakeRunner(
        [{"kind": "epoch", "message": "epoch 1/2", "progress": 0.5, "data": {}}]
    )
    worker.run_worker(run_dir, runner=runner)
    log = (run_dir / "stdout.log").read_text(encoding="utf-8")
    assert "epoch 1/2" in log


def test_run_worker_error_event_yields_nonzero_exit(tmp_path: Path) -> None:
    """An error TrainingEvent makes the worker exit non-zero."""
    run_dir = tmp_path / "runs" / "run-1"
    _write_run_dir(run_dir)
    runner = _FakeRunner(
        [{"kind": "error", "message": "RuntimeError: CUDA out of memory"}]
    )
    code = worker.run_worker(run_dir, runner=runner)
    assert code == 1


def test_run_worker_applies_dataset_env(tmp_path: Path, monkeypatch) -> None:
    """The worker exports PD_OCR_TRAINER_ML_* env vars from the manifest args."""
    run_dir = tmp_path / "runs" / "run-1"
    _write_run_dir(run_dir)
    monkeypatch.delenv("PD_OCR_TRAINER_ML_TRAINING_DIR", raising=False)
    runner = _FakeRunner([{"kind": "done", "message": "ok"}])
    worker.run_worker(run_dir, runner=runner)
    import os

    assert os.environ["PD_OCR_TRAINER_ML_TRAINING_DIR"].endswith("ml-training")


def test_emit_event_format() -> None:
    """emit_event writes a single @@PDEVENT@@-prefixed JSON line."""
    import io
    import sys

    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        worker.emit_event({"kind": "log", "message": "hello"})
    finally:
        sys.stdout = old
    line = buf.getvalue().strip()
    assert line.startswith("@@PDEVENT@@ ")
    assert json.loads(line[len("@@PDEVENT@@") :])["message"] == "hello"
