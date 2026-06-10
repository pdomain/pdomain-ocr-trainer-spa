"""Worker dispatch tests — _iter_events routes tasks to train_* methods (M12).

Issue 3 fix: uses FakeTrainingRunner from the shared injectable seam
(training/fake_runner.py) rather than an inline per-test stub.
"""

from __future__ import annotations

from pathlib import Path

from pdomain_ocr_trainer_spa.training.fake_runner import FakeTrainingRunner


def test_iter_events_routes_detection(tmp_path: Path) -> None:
    """_iter_events routes task='detection' to train_detection."""
    from pdomain_ocr_trainer_spa.worker.train import _iter_events

    runner = FakeTrainingRunner()
    args: dict[str, object] = {
        "train_path": str(tmp_path / "train"),
        "val_path": str(tmp_path / "val"),
        "output_dir": str(tmp_path / "out"),
    }
    events = list(_iter_events(runner, task="detection", profile="test", args=args))  # type: ignore[arg-type]
    kinds = [getattr(e, "kind", None) for e in events]
    assert "done" in kinds


def test_iter_events_routes_recognition(tmp_path: Path) -> None:
    """_iter_events routes task='recognition' to train_recognition."""
    from pdomain_ocr_trainer_spa.worker.train import _iter_events

    runner = FakeTrainingRunner()
    args: dict[str, object] = {
        "train_path": str(tmp_path / "train"),
        "val_path": str(tmp_path / "val"),
        "output_dir": str(tmp_path / "out"),
        "vocab": "french",
    }
    events = list(_iter_events(runner, task="recognition", profile="test", args=args))  # type: ignore[arg-type]
    kinds = [getattr(e, "kind", None) for e in events]
    assert "done" in kinds


def test_iter_events_typeface_calls_train_typeface(tmp_path: Path) -> None:
    """_iter_events routes typeface-classification to train_typeface (shared seam)."""
    from pdomain_ocr_trainer_spa.worker.train import _iter_events

    runner = FakeTrainingRunner()
    args: dict[str, object] = {
        "train_path": str(tmp_path / "train"),
        "val_path": str(tmp_path / "val"),
        "output_dir": str(tmp_path / "out"),
    }
    events = list(_iter_events(runner, task="typeface-classification", profile="test", args=args))  # type: ignore[arg-type]
    kinds = [getattr(e, "kind", None) for e in events]
    assert "done" in kinds
    # Metric events should carry accuracy + f1_macro data
    metric_events = [e for e in events if getattr(e, "kind", None) == "metric"]
    assert len(metric_events) >= 1
    assert metric_events[0].data is not None
    assert "accuracy" in metric_events[0].data
    assert "f1_macro" in metric_events[0].data
