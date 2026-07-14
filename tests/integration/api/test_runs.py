"""Integration tests for api/runs.py — the training-run lifecycle.

Covers the six acceptance scenarios from specs/06-training-runs.md §10 using
the FakeLongJobRunner (spec 14-testing §2.1). No real subprocess, no GPU.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pdomain_ops.gpu.types import JobEvent

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from pdomain_ocr_trainer_spa.settings import Settings
    from pdomain_ocr_trainer_spa.training.fake_runner import FakeLongJobRunner


def _ev(kind: str, payload: dict[str, object]) -> JobEvent:
    return JobEvent.model_construct(job_id="", seq=0, at=None, kind=kind, payload=payload)


_SUCCESS_SCRIPT = [
    _ev("log", {"stream": "stdout", "line": "epoch 1/3"}),
    _ev("progress", {"current": 1, "total": 3, "message": "epoch 1/3"}),
    _ev("metric", {"name": "val_cer", "value": 0.10, "step": 1}),
    _ev("progress", {"current": 2, "total": 3, "message": "epoch 2/3"}),
    _ev("metric", {"name": "val_cer", "value": 0.05, "step": 2}),
    _ev("progress", {"current": 3, "total": 3, "message": "epoch 3/3"}),
    _ev("state", {"state": "succeeded", "exit_code": 0}),
]


# --- Scenario 1: create a run --------------------------------------------


def test_scenario1_create_run(
    client: TestClient, fake_runner: FakeLongJobRunner, trained_profile: str
) -> None:
    """New run → form args accepted → 202 with run_id + job_id; status running."""
    fake_runner.script = list(_SUCCESS_SCRIPT)
    r = client.post(
        "/api/runs",
        json={"profile": trained_profile, "task": "recognition", "args": {"epochs": 5}},
    )
    assert r.status_code == 202
    body = r.json()
    assert body["run_id"]
    assert body["job_id"]

    # The run is submitted as `running`; a GET reconciles against the job.
    listed = client.get("/api/runs").json()["runs"]
    created = next(r for r in listed if r["id"] == body["run_id"])
    assert created["model_name"].startswith("pd-ga-clogaelach-recognition-")
    assert created["args"]["epochs"] == 5
    assert created["job_id"] == body["job_id"]

    detail = client.get(f"/api/runs/{body['run_id']}")
    assert detail.status_code == 200
    assert detail.json()["status"] in {"running", "succeeded"}


def test_create_run_no_training_data_409(client: TestClient, fake_runner: FakeLongJobRunner) -> None:
    """A profile without labels.json is rejected before submission."""
    from pdomain_ocr_trainer_spa.core.enums import TypefaceEnum
    from pdomain_ocr_trainer_spa.domain.profiles import create_profile

    state = client.app.state.app_state  # type: ignore[attr-defined]  # test fixture installs this FastAPI state attribute
    create_profile(state.settings, name="empty", language="ga", typeface=TypefaceEnum.roman)
    fake_runner.script = list(_SUCCESS_SCRIPT)
    r = client.post("/api/runs", json={"profile": "empty", "task": "recognition", "args": {}})
    assert r.status_code == 409
    assert r.json()["code"] == "run.no_training_data"


def test_create_run_incomplete_profile_409(
    client: TestClient, fake_runner: FakeLongJobRunner, settings: Settings
) -> None:
    """A profile lacking language/typeface blocks model-name derivation."""
    from pdomain_ocr_trainer_spa.domain.profiles import create_profile

    create_profile(settings, name="bare")
    task_dir = settings.ml_training_dir / "bare" / "recognition"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "labels.json").write_text(json.dumps({"c": "x"}), encoding="utf-8")
    fake_runner.script = list(_SUCCESS_SCRIPT)
    r = client.post("/api/runs", json={"profile": "bare", "task": "recognition", "args": {}})
    assert r.status_code == 409
    assert r.json()["code"] == "run.profile_incomplete"


# --- Scenario 2 + 3: status transitions, log + metric streaming -----------


def test_scenario2_3_status_and_sse_stream(
    client: TestClient, fake_runner: FakeLongJobRunner, trained_profile: str
) -> None:
    """Status reaches running; SSE streams log + progress + metric frames."""
    fake_runner.script = list(_SUCCESS_SCRIPT)
    r = client.post(
        "/api/runs",
        json={"profile": trained_profile, "task": "detection", "args": {"epochs": 3}},
    )
    job_id = r.json()["job_id"]

    with client.stream("GET", f"/api/jobs/{job_id}/events") as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
    assert "event: log" in body
    assert "event: progress" in body
    assert "event: metric" in body
    assert "event: state" in body


def test_scenario3_progress_jsonl_populated(
    client: TestClient, fake_runner: FakeLongJobRunner, trained_profile: str
) -> None:
    """Streaming the SSE log appends progress + metric events to progress.jsonl."""
    fake_runner.script = list(_SUCCESS_SCRIPT)
    r = client.post(
        "/api/runs",
        json={"profile": trained_profile, "task": "recognition", "args": {"epochs": 3}},
    )
    run_id, job_id = r.json()["run_id"], r.json()["job_id"]

    with client.stream("GET", f"/api/jobs/{job_id}/events") as resp:
        "".join(resp.iter_text())

    progress = client.get(f"/api/runs/{run_id}/progress")
    assert progress.status_code == 200
    records = progress.json()["records"]
    kinds = {rec["type"] for rec in records}
    assert kinds == {"progress", "metric"}


# --- Scenario 4: cancel ---------------------------------------------------


def test_scenario4_cancel_run(
    client: TestClient, fake_runner: FakeLongJobRunner, trained_profile: str
) -> None:
    """Cancel flips the run to cancelled and cancels the owning job."""
    fake_runner.script = list(_SUCCESS_SCRIPT)
    r = client.post(
        "/api/runs",
        json={"profile": trained_profile, "task": "recognition", "args": {}},
    )
    run_id = r.json()["run_id"]

    cancel = client.post(f"/api/runs/{run_id}/cancel")
    assert cancel.status_code == 202
    assert cancel.json()["status"] == "cancelled"

    detail = client.get(f"/api/runs/{run_id}")
    assert detail.json()["status"] == "cancelled"


# --- Scenario 5: reload mid-run (SSE reconnect via Last-Event-ID) ---------


def test_scenario5_sse_reconnect_replays_remainder(
    client: TestClient, fake_runner: FakeLongJobRunner, trained_profile: str
) -> None:
    """Reconnecting with Last-Event-ID skips already-seen events."""
    fake_runner.script = list(_SUCCESS_SCRIPT)
    r = client.post(
        "/api/runs",
        json={"profile": trained_profile, "task": "recognition", "args": {}},
    )
    job_id = r.json()["job_id"]

    with client.stream("GET", f"/api/jobs/{job_id}/events", headers={"Last-Event-ID": "3"}) as resp:
        body = "".join(resp.iter_text())
    # events with seq <= 3 are skipped; seq 4,5,6 remain
    assert "id: 0" not in body
    assert "id: 3" not in body
    assert "id: 4" in body
    assert "id: 6" in body


# --- Scenario 6: completion -> terminal status ----------------------------


def test_scenario6_run_succeeds_after_completion(
    client: TestClient, fake_runner: FakeLongJobRunner, trained_profile: str
) -> None:
    """After the job reports succeeded, the run reconciles to succeeded."""
    fake_runner.script = list(_SUCCESS_SCRIPT)
    r = client.post(
        "/api/runs",
        json={"profile": trained_profile, "task": "recognition", "args": {}},
    )
    run_id = r.json()["run_id"]

    detail = client.get(f"/api/runs/{run_id}")
    assert detail.json()["status"] == "succeeded"
    assert detail.json()["exit_code"] == 0


def test_run_fails_when_job_fails(
    client: TestClient, fake_runner: FakeLongJobRunner, trained_profile: str
) -> None:
    """A failed job reconciles the run to failed with a non-zero exit code."""
    fake_runner.script = [
        _ev("log", {"line": "starting"}),
        _ev("state", {"state": "failed", "exit_code": 1}),
    ]
    r = client.post(
        "/api/runs",
        json={"profile": trained_profile, "task": "recognition", "args": {}},
    )
    run_id = r.json()["run_id"]
    detail = client.get(f"/api/runs/{run_id}")
    assert detail.json()["status"] == "failed"
    assert detail.json()["exit_code"] == 1


# --- list / concurrency / delete ------------------------------------------


def test_list_runs(client: TestClient, fake_runner: FakeLongJobRunner, trained_profile: str) -> None:
    """The run list returns created runs newest-first."""
    fake_runner.script = list(_SUCCESS_SCRIPT)
    client.post("/api/runs", json={"profile": trained_profile, "task": "recognition", "args": {}})
    r = client.get("/api/runs")
    assert r.status_code == 200
    assert len(r.json()["runs"]) == 1


def test_one_train_job_at_a_time(
    client: TestClient, fake_runner: FakeLongJobRunner, trained_profile: str
) -> None:
    """A second submission while one run is pending/running is a 409 (D-T15)."""
    fake_runner.script = [_ev("log", {"line": "running"})]  # no terminal event
    first = client.post("/api/runs", json={"profile": trained_profile, "task": "recognition", "args": {}})
    assert first.status_code == 202
    second = client.post("/api/runs", json={"profile": trained_profile, "task": "detection", "args": {}})
    assert second.status_code == 409
    assert second.json()["code"] == "run.already_running"


def test_delete_terminal_run(
    client: TestClient, fake_runner: FakeLongJobRunner, trained_profile: str
) -> None:
    """A succeeded run with no artefacts can be deleted."""
    fake_runner.script = list(_SUCCESS_SCRIPT)
    r = client.post("/api/runs", json={"profile": trained_profile, "task": "recognition", "args": {}})
    run_id = r.json()["run_id"]
    client.get(f"/api/runs/{run_id}")  # reconcile to succeeded
    assert client.delete(f"/api/runs/{run_id}").status_code == 204
    assert client.get(f"/api/runs/{run_id}").status_code == 404


def test_get_unknown_run_404(client: TestClient) -> None:
    """An unknown run id is a 404."""
    r = client.get("/api/runs/nope")
    assert r.status_code == 404
    assert r.json()["code"] == "run.unknown"


# --- crash recovery (D-T3) ------------------------------------------------


def test_hydrate_marks_orphaned_running_as_failed(settings: Settings, trained_profile: str) -> None:
    """A run left 'running' at boot with no live job is marked failed."""
    from pdomain_ocr_trainer_spa.bootstrap import build_app
    from pdomain_ocr_trainer_spa.core.enums import TaskEnum
    from pdomain_ocr_trainer_spa.domain import runs as dom

    run = dom.create_run(settings, profile=trained_profile, task=TaskEnum.recognition, args={})
    dom.update_run(settings, run, status="running", job_id="dead-job")

    app = build_app(settings)  # triggers hydrate_from_disk
    state = app.state.app_state
    recovered = state.runs[run.id]
    assert recovered.status == "failed"
    assert recovered.exit_code == -1
    stderr = dom.run_dir(settings, run.id) / "stderr.log"
    assert "process gone" in stderr.read_text(encoding="utf-8")
