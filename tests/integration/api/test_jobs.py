"""Integration tests for api/jobs.py — the SPA Job projection + SSE stream.

Driven by the FakeLongJobRunner (spec 14-testing §2.1 / §2.3). No real
subprocess, no GPU. The SSE route is exercised end to end:
route -> LongJobRunner.stream_events -> SSE frame.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from pdomain_ocr_ops.gpu.types import JobEvent

if TYPE_CHECKING:

    from pdomain_ocr_trainer_spa.training.fake_runner import FakeLongJobRunner


@pytest.fixture
def fake_runner(app) -> FakeLongJobRunner:
    """The app's wired-in FakeLongJobRunner (Settings.job_runner_kind='fake')."""
    return app.state.app_state.job_runner


_SCRIPT = [
    JobEvent.model_construct(
        job_id="", seq=0, at=None, kind="log",
        payload={"stream": "stdout", "line": "Epoch 1/3"},
    ),
    JobEvent.model_construct(
        job_id="", seq=0, at=None, kind="progress",
        payload={"current": 1, "total": 3, "message": "epoch 1/3"},
    ),
    JobEvent.model_construct(
        job_id="", seq=0, at=None, kind="metric",
        payload={"name": "val_cer", "value": 0.10, "step": 1},
    ),
    JobEvent.model_construct(
        job_id="", seq=0, at=None, kind="progress",
        payload={"current": 2, "total": 3, "message": "epoch 2/3"},
    ),
    JobEvent.model_construct(
        job_id="", seq=0, at=None, kind="state",
        payload={"state": "succeeded", "exit_code": 0},
    ),
]


def _parse_sse(raw: str) -> list[dict[str, object]]:
    """Parse an SSE byte stream into a list of {id, event, data} frames."""
    frames: list[dict[str, object]] = []
    current: dict[str, object] = {}
    for line in raw.splitlines():
        if line == "":
            if "data" in current:
                frames.append(current)
            current = {}
            continue
        if line.startswith(":"):
            continue  # keep-alive comment
        field, _, value = line.partition(":")
        value = value.lstrip()
        if field == "id":
            current["id"] = int(value)
        elif field == "event":
            current["event"] = value
        elif field == "data":
            current["data"] = json.loads(value)
        elif field == "retry":
            current["retry"] = int(value)
    return frames


def _submit(fake_runner: FakeLongJobRunner) -> str:
    """Script the fake runner and submit a synthetic job; return job_id."""
    import asyncio

    fake_runner.script = list(_SCRIPT)
    return asyncio.run(fake_runner.submit("train.recognition", {}))


# --- GET /api/jobs/{id} -----------------------------------------------------


def test_get_job_projects_jobstatus(client, fake_runner) -> None:
    """GET /api/jobs/{id} projects JobStatus onto the SPA Job model."""
    job_id = _submit(fake_runner)
    r = client.get(f"/api/jobs/{job_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == job_id
    assert body["kind"] == "train.recognition"
    assert body["state"] in {"running", "succeeded"}
    assert body["run_id"] is None
    assert 0.0 <= body["progress"] <= 1.0


def test_get_unknown_job_404(client) -> None:
    """An unknown job_id yields 404 job.unknown."""
    r = client.get("/api/jobs/does-not-exist")
    assert r.status_code == 404
    assert r.json()["code"] == "job.unknown"


# --- GET /api/jobs/{id}/events ---------------------------------------------


def test_subscribe_receives_every_event_in_order(client, fake_runner) -> None:
    """Acceptance 1: subscribe; receive every scripted event in order."""
    job_id = _submit(fake_runner)
    with client.stream("GET", f"/api/jobs/{job_id}/events") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        raw = "".join(resp.iter_text())
    frames = _parse_sse(raw)
    assert [f["event"] for f in frames] == [
        "log", "progress", "metric", "progress", "state",
    ]
    seqs = [f["id"] for f in frames]
    assert seqs == sorted(seqs)
    assert frames[-1]["data"]["payload"]["state"] == "succeeded"


def test_reconnect_with_last_event_id_replays_missed(client, fake_runner) -> None:
    """Acceptance 2: reconnect with Last-Event-ID; only later events replay."""
    job_id = _submit(fake_runner)
    with client.stream("GET", f"/api/jobs/{job_id}/events") as resp:
        raw = "".join(resp.iter_text())
    all_frames = _parse_sse(raw)
    cutoff = all_frames[1]["id"]  # pretend the client saw frames 0 and 1

    with client.stream(
        "GET",
        f"/api/jobs/{job_id}/events",
        headers={"Last-Event-ID": str(cutoff)},
    ) as resp:
        replay_raw = "".join(resp.iter_text())
    replay = _parse_sse(replay_raw)
    assert all(f["id"] > cutoff for f in replay)
    # Frames 0=log, 1=progress were "seen"; replay resumes at 2=metric.
    assert [f["event"] for f in replay] == ["metric", "progress", "state"]


def test_unknown_job_events_404(client) -> None:
    """Streaming an unknown job_id yields 404 before the stream opens."""
    r = client.get("/api/jobs/nope/events")
    assert r.status_code == 404
    assert r.json()["code"] == "job.unknown"


# --- POST /api/jobs/{id}/cancel --------------------------------------------


def test_cancel_emits_terminal_state_and_suppresses(client, fake_runner) -> None:
    """Acceptance 3: cancel; terminal state event fires; later events suppressed."""
    job_id = _submit(fake_runner)
    r = client.post(f"/api/jobs/{job_id}/cancel")
    assert r.status_code == 202
    body = r.json()
    assert body["id"] == job_id
    assert body["state"] == "cancelled"

    # The job status reflects the terminal cancelled state.
    status = client.get(f"/api/jobs/{job_id}")
    assert status.json()["state"] == "cancelled"

    # Subsequent stream is suppressed — no scripted events leak after cancel.
    with client.stream("GET", f"/api/jobs/{job_id}/events") as resp:
        raw = "".join(resp.iter_text())
    frames = _parse_sse(raw)
    assert frames == []


def test_cancel_unknown_job_404(client) -> None:
    """Cancelling an unknown job_id yields 404 job.unknown."""
    r = client.post("/api/jobs/nope/cancel")
    assert r.status_code == 404
    assert r.json()["code"] == "job.unknown"


# --- GET /api/jobs/active-count --------------------------------------------


def test_active_count(client, fake_runner) -> None:
    """active-count reports non-terminal jobs grouped by kind."""
    import asyncio

    # A script with no terminal `state` event keeps the job `running`.
    fake_runner.script = [
        JobEvent.model_construct(
            job_id="", seq=0, at=None, kind="progress",
            payload={"current": 1, "total": 3, "message": "epoch 1/3"},
        ),
    ]
    asyncio.run(fake_runner.submit("train.recognition", {}))
    r = client.get("/api/jobs/active-count")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["by_kind"] == {"train.recognition": 1}


def test_active_count_excludes_terminal(client, fake_runner) -> None:
    """A job whose script ends in a terminal state is not counted as active."""
    _submit(fake_runner)  # script ends with state=succeeded
    r = client.get("/api/jobs/active-count")
    assert r.status_code == 200
    assert r.json() == {"count": 0, "by_kind": {}}
