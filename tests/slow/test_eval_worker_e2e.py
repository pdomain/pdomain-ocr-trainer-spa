"""Slow e2e test: real LocalLongJobRunner.submit_with_process + stub eval worker.

Exercises the eval round-trip end-to-end (spec 07 §8 acceptance): an eval run
submitted to a real subprocess produces ``runs/<id>/result.json`` on disk,
which the eval API then reads back.

Marked ``slow``: excluded from the default ``make test`` run.
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

_STUB_EVAL_WORKER = Path(__file__).parent.parent / "fixtures" / "stub_eval_worker.py"

pytestmark = pytest.mark.slow


async def _submit_and_wait(
    runner: object, *, kind: str, run_id: str, cmd: list[str], timeout_s: float = 15.0
) -> str:
    """Submit a process job and poll to terminal state in one event loop."""
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


def test_eval_round_trip_writes_result_json(settings: Settings) -> None:
    """An eval run via a real subprocess writes result.json the API can read."""
    from pdomain_ops.gpu.local_jobs import LocalLongJobRunner

    from pdomain_ocr_trainer_spa.core.enums import TaskEnum, TypefaceEnum
    from pdomain_ocr_trainer_spa.domain import eval as eval_dom
    from pdomain_ocr_trainer_spa.domain.profiles import create_profile

    create_profile(
        settings, name="clogaelach", language="ga", typeface=TypefaceEnum.clogaelach
    )
    # Seed a model on disk so create_eval_run validates.
    name = "pd-ga-clogaelach-recognition-2026-05-05"
    leaf = settings.shared_models_dir / "clogaelach" / "recognition" / name
    leaf.mkdir(parents=True, exist_ok=True)
    (leaf / "model.pt").write_bytes(b"\x00")

    run = eval_dom.create_eval_run(
        settings,
        profile="clogaelach",
        task=TaskEnum.recognition,
        model_name=name,
    )

    assert settings.jobs_db_path is not None
    settings.jobs_db_path.parent.mkdir(parents=True, exist_ok=True)
    runner = LocalLongJobRunner(db_path=settings.jobs_db_path, poll_interval_s=0.1)
    cmd = [
        sys.executable,
        str(_STUB_EVAL_WORKER),
        "--run-dir",
        str(settings.runs_dir / run.id),
    ]

    state = asyncio.run(
        _submit_and_wait(runner, kind="eval.recognition", run_id=run.id, cmd=cmd)
    )
    assert state == "succeeded"

    result_path = settings.runs_dir / run.id / "result.json"
    assert result_path.exists()
    result = eval_dom.read_result(settings, run.id)
    assert result is not None
    assert result.overall.cer == json.loads(result_path.read_text())["overall"]["cer"]
