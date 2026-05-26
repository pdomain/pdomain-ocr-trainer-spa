"""Unit tests for worker/evaluate.py — torch-free, with an injected fake runner.

The eval worker drives an injected fake :class:`EvalRunner`, so no torch /
DocTR / GPU is touched (spec 14-testing §5).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from pdomain_ocr_trainer_spa.core.models import EvalMetrics
from pdomain_ocr_trainer_spa.worker import evaluate as worker

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


class _FakeEvalRunner:
    """Torch-free stand-in — returns scripted metrics."""

    def __init__(self, metrics: EvalMetrics, sample_count: int) -> None:
        self._metrics = metrics
        self._sample_count = sample_count

    def evaluate(
        self,
        *,
        task: str,
        profile: str,
        model_name: str,
        val_source: str,
        options: Mapping[str, object],
    ) -> tuple[EvalMetrics, int]:
        del task, profile, model_name, val_source, options
        return self._metrics, self._sample_count


def _write_run_dir(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "id": run_dir.name,
                "profile": "clogaelach",
                "task": "recognition",
                "model_name": "pd-ga-clogaelach-recognition-2026-05-05",
                "args": {},
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "args.json").write_text(
        json.dumps(
            {
                "model_name": "pd-ga-clogaelach-recognition-2026-05-05",
                "val_source": "local:ml-validation/clogaelach/recognition",
            }
        ),
        encoding="utf-8",
    )


def test_run_worker_writes_result_json(tmp_path: Path) -> None:
    """A successful eval writes runs/<id>/result.json with the metrics."""
    run_dir = tmp_path / "runs" / "eval-1"
    _write_run_dir(run_dir)
    runner = _FakeEvalRunner(EvalMetrics(cer=0.034, wer=0.092), 1842)
    code = worker.run_worker(run_dir, runner=runner)
    assert code == 0
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert result["overall"]["cer"] == pytest.approx(0.034)
    assert result["sample_count"] == 1842
    assert result["run_id"] == "eval-1"


def test_run_worker_emits_done_event(tmp_path: Path, capsys) -> None:
    """The eval worker emits a done @@PDEVENT@@ line on success."""
    run_dir = tmp_path / "runs" / "eval-1"
    _write_run_dir(run_dir)
    runner = _FakeEvalRunner(EvalMetrics(cer=0.05), 10)
    worker.run_worker(run_dir, runner=runner)
    lines = [
        ln for ln in capsys.readouterr().out.splitlines()
        if ln.startswith("@@PDEVENT@@")
    ]
    kinds = [json.loads(ln[len("@@PDEVENT@@") :])["kind"] for ln in lines]
    assert "done" in kinds


def test_run_worker_runner_failure_exits_nonzero(tmp_path: Path) -> None:
    """An exception from the runner makes the worker exit non-zero."""
    run_dir = tmp_path / "runs" / "eval-1"
    _write_run_dir(run_dir)

    class _Boom:
        def evaluate(self, **_: object) -> tuple[EvalMetrics, int]:
            raise RuntimeError("model load failed")

    code = worker.run_worker(run_dir, runner=_Boom())
    assert code == 1
    assert not (run_dir / "result.json").exists()


def test_build_runner_surfaces_upstream_gap() -> None:
    """The production runner path raises a clear upstream-gap error."""
    with pytest.raises(RuntimeError, match="pdomain-ocr-training"):
        worker._build_runner()
