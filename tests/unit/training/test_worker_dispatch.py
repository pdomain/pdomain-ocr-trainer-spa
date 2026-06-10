"""Worker dispatch tests — _iter_events routes tasks to train_* methods (M12)."""

from __future__ import annotations

from pathlib import Path


class _FakeTrainingRunner:
    """Minimal torch-free runner stub for testing _iter_events routing."""

    def __init__(self) -> None:
        self.called: str | None = None

    def train_detection(self, profile: str, config: object):  # type: ignore[override]
        del profile, config
        self.called = "detection"
        from pdomain_ocr_training.protocols import TrainingEvent

        yield TrainingEvent(kind="done", message="done", progress=1.0)

    def train_recognition(self, profile: str, config: object):  # type: ignore[override]
        del profile, config
        self.called = "recognition"
        from pdomain_ocr_training.protocols import TrainingEvent

        yield TrainingEvent(kind="done", message="done", progress=1.0)

    def train_typeface(self, profile: str, config: object):  # type: ignore[override]
        del profile, config
        self.called = "typeface"
        from pdomain_ocr_training.protocols import TrainingEvent

        yield TrainingEvent(
            kind="metric", message="epoch 1", progress=0.5, data={"accuracy": 0.85, "f1_macro": 0.83}
        )
        yield TrainingEvent(kind="done", message="training complete", progress=1.0)


def test_iter_events_routes_detection(tmp_path: Path) -> None:
    """_iter_events routes task='detection' to train_detection."""
    from pdomain_ocr_trainer_spa.worker.train import _iter_events

    runner = _FakeTrainingRunner()
    args: dict[str, object] = {
        "train_path": str(tmp_path / "train"),
        "val_path": str(tmp_path / "val"),
        "output_dir": str(tmp_path / "out"),
    }
    events = list(_iter_events(runner, task="detection", profile="test", args=args))  # type: ignore[arg-type]
    assert runner.called == "detection"
    kinds = [getattr(e, "kind", None) for e in events]
    assert "done" in kinds


def test_iter_events_routes_recognition(tmp_path: Path) -> None:
    """_iter_events routes task='recognition' to train_recognition."""
    from pdomain_ocr_trainer_spa.worker.train import _iter_events

    runner = _FakeTrainingRunner()
    args: dict[str, object] = {
        "train_path": str(tmp_path / "train"),
        "val_path": str(tmp_path / "val"),
        "output_dir": str(tmp_path / "out"),
        "vocab": "french",
    }
    events = list(_iter_events(runner, task="recognition", profile="test", args=args))  # type: ignore[arg-type]
    assert runner.called == "recognition"
    kinds = [getattr(e, "kind", None) for e in events]
    assert "done" in kinds


def test_iter_events_typeface_calls_train_typeface(tmp_path: Path) -> None:
    """_iter_events routes typeface-classification to train_typeface."""
    from pdomain_ocr_trainer_spa.worker.train import _iter_events

    runner = _FakeTrainingRunner()
    args: dict[str, object] = {
        "train_path": str(tmp_path / "train"),
        "val_path": str(tmp_path / "val"),
        "output_dir": str(tmp_path / "out"),
    }
    events = list(_iter_events(runner, task="typeface-classification", profile="test", args=args))  # type: ignore[arg-type]
    assert runner.called == "typeface"
    kinds = [getattr(e, "kind", None) for e in events]
    assert "done" in kinds
    # Metric event should carry accuracy data
    metric_events = [e for e in events if getattr(e, "kind", None) == "metric"]
    assert len(metric_events) == 1
    assert metric_events[0].data is not None
    assert "accuracy" in metric_events[0].data
