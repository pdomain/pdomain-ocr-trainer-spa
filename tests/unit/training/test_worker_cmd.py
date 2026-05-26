"""worker_cmd tests — build_worker_cmd argv shape."""

from __future__ import annotations

import sys


class _Run:
    id = "run-abc"


def test_build_worker_cmd_argv(settings) -> None:
    from pdomain_ocr_trainer_spa.training.worker_cmd import build_worker_cmd

    cmd = build_worker_cmd(_Run(), settings)
    assert cmd[:4] == [sys.executable, "-m", "pdomain_ocr_trainer_spa.worker.train", "--run-dir"]
    assert cmd[4] == str(settings.runs_dir / "run-abc")
