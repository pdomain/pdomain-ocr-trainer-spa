"""FakeLongJobRunner tests — scripted events, lifecycle, cancellation."""

from __future__ import annotations

from datetime import UTC, datetime

from pdomain_ops.gpu.protocols import LongJobRunner
from pdomain_ops.gpu.types import JobEvent

from pdomain_ocr_trainer_spa.training.fake_runner import FakeLongJobRunner


def _event(kind: str, payload: dict[str, object]) -> JobEvent:
    return JobEvent(job_id="_", seq=0, at=datetime.now(UTC), kind=kind, payload=payload)


def test_fake_runner_satisfies_protocol() -> None:
    assert isinstance(FakeLongJobRunner(), LongJobRunner)


async def test_submit_registers_running_job() -> None:
    runner = FakeLongJobRunner()
    job_id = await runner.submit("train.detection", {})
    status = await runner.status(job_id)
    assert status.job_id == job_id
    assert status.kind == "train.detection"


async def test_submit_with_process_registers_job() -> None:
    runner = FakeLongJobRunner()
    job_id = await runner.submit_with_process("train.detection", {}, ["echo", "hi"])
    assert (await runner.status(job_id)).job_id == job_id


async def test_stream_events_replays_script() -> None:
    runner = FakeLongJobRunner()
    runner.script = [
        _event("log", {"line": "epoch 1/2"}),
        _event("progress", {"current": 1, "total": 2}),
        _event("state", {"state": "succeeded", "exit_code": 0}),
    ]
    job_id = await runner.submit("train.detection", {})
    events = [e async for e in runner.stream_events(job_id)]
    assert [e.kind for e in events] == ["log", "progress", "state"]
    assert [e.seq for e in events] == [0, 1, 2]


async def test_status_reflects_terminal_state_from_script() -> None:
    runner = FakeLongJobRunner()
    runner.script = [_event("state", {"state": "succeeded", "exit_code": 0})]
    job_id = await runner.submit("train.detection", {})
    assert (await runner.status(job_id)).state == "succeeded"


async def test_cancel_flips_state_and_suppresses_events() -> None:
    runner = FakeLongJobRunner()
    runner.script = [
        _event("progress", {"current": 1, "total": 3}),
        _event("state", {"state": "succeeded", "exit_code": 0}),
    ]
    job_id = await runner.submit("train.detection", {})
    await runner.cancel(job_id)
    assert (await runner.status(job_id)).state == "cancelled"
    assert [e async for e in runner.stream_events(job_id)] == []
