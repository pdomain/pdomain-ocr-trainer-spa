"""Slow e2e test: real LocalLongJobRunner.submit_with_process + stub_worker.py.

Exercises the actual subprocess plumbing — env var passing, line buffering,
exit-code -> job state — without CUDA or DocTR (spec 14-testing §5.3).

Marked ``slow``: excluded from the default ``make test`` run, executed by
``make test-slow``.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.settings import Settings

_STUB_WORKER = Path(__file__).parent.parent / "fixtures" / "stub_worker.py"

pytestmark = pytest.mark.slow


async def _submit_and_wait(
    runner: object, *, kind: str, run_id: str, cmd: list[str], timeout_s: float = 15.0
) -> str:
    """Submit a process job and poll to terminal state in one event loop.

    ``submit_with_process`` schedules supervision via ``asyncio.create_task``;
    submission and polling must share an event loop or the supervisor never
    runs.
    """
    job_id = await runner.submit_with_process(  # type: ignore[attr-defined]
        kind=kind, spec={"run_id": run_id}, cmd=cmd
    )
    deadline = asyncio.get_event_loop().time() + timeout_s
    while asyncio.get_event_loop().time() < deadline:
        status = await runner.status(job_id)  # type: ignore[attr-defined]
        if status.state in {"succeeded", "failed", "cancelled"}:
            return str(status.state)
        await asyncio.sleep(0.1)
    return "timeout"


def test_stub_worker_runs_to_completion(settings: Settings) -> None:
    """A real subprocess running the stub worker drives the job to succeeded."""
    from pdomain_ops.gpu.local_jobs import LocalLongJobRunner

    # Seed a profile + recognition training data so create_run validates.
    from pdomain_ocr_trainer_spa.core.enums import TaskEnum, TypefaceEnum
    from pdomain_ocr_trainer_spa.domain import runs as dom
    from pdomain_ocr_trainer_spa.domain.profiles import create_profile

    create_profile(settings, name="clogaelach", language="ga", typeface=TypefaceEnum.clogaelach)
    task_dir = settings.ml_training_dir / "clogaelach" / "recognition"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "labels.json").write_text(json.dumps({"c": "x"}), encoding="utf-8")

    run = dom.create_run(
        settings,
        profile="clogaelach",
        task=TaskEnum.recognition,
        args={"epochs": 3},
    )

    assert settings.jobs_db_path is not None
    settings.jobs_db_path.parent.mkdir(parents=True, exist_ok=True)
    runner = LocalLongJobRunner(db_path=settings.jobs_db_path, poll_interval_s=0.1)
    cmd = [
        sys.executable,
        str(_STUB_WORKER),
        "--run-dir",
        str(dom.run_dir(settings, run.id)),
    ]

    state = asyncio.run(_submit_and_wait(runner, kind="train.recognition", run_id=run.id, cmd=cmd))
    assert state == "succeeded"


def test_stub_worker_emits_pdevent_lines(settings: Settings, tmp_path: Path) -> None:
    """The stub worker emits a well-formed @@PDEVENT@@ sequence ending in done."""
    import subprocess

    run_dir = tmp_path / "runs" / "stub-run"
    run_dir.mkdir(parents=True)
    (run_dir / "args.json").write_text(json.dumps({"epochs": 2}), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(_STUB_WORKER), "--run-dir", str(run_dir)],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    events = [
        json.loads(ln[len("@@PDEVENT@@") :])
        for ln in result.stdout.splitlines()
        if ln.startswith("@@PDEVENT@@")
    ]
    assert events[-1]["kind"] == "done"
    assert any(e["kind"] == "epoch" for e in events)
    assert any(e["kind"] == "metric" for e in events)
