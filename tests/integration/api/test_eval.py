"""Integration tests for api/eval.py — the eval REST surface (spec 07).

The FakeLongJobRunner does not run the worker subprocess, so the eval
round-trip is exercised by submitting the eval (202), invoking the eval
worker in-process with a torch-free fake runner to produce result.json, and
then reading the result back through the API — proving the API → domain →
worker → result chain end-to-end.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pdomain_ocr_trainer_spa.core.models import EvalMetrics, ModelSidecar

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from pdomain_ocr_trainer_spa.settings import Settings
    from pdomain_ocr_trainer_spa.training.fake_runner import FakeLongJobRunner


def _seed_model(settings: Settings) -> str:
    name = "pd-ga-clogaelach-recognition-2026-05-05"
    leaf = settings.shared_models_dir / "clogaelach" / "recognition" / name
    leaf.mkdir(parents=True, exist_ok=True)
    (leaf / "model.pt").write_bytes(b"\x00")
    (leaf / f"{name}.metadata.json").write_text(
        ModelSidecar(name=name, task="recognition", language="ga").model_dump_json()
    )
    return name


class _FakeEvalRunner:
    def evaluate(self, **_: object) -> tuple[EvalMetrics, int]:
        return EvalMetrics(cer=0.034, wer=0.092), 1842


def test_create_eval_returns_202(
    client: TestClient, settings: Settings, trained_profile: str
) -> None:
    """POST /api/eval creates an eval run and returns 202 with run+job ids."""
    model = _seed_model(settings)
    r = client.post(
        "/api/eval",
        json={"profile": trained_profile, "task": "recognition", "model_name": model},
    )
    assert r.status_code == 202
    body = r.json()
    assert body["run_id"]
    assert body["job_id"]


def test_create_eval_unknown_model_404(
    client: TestClient, trained_profile: str
) -> None:
    """An eval against a missing model is rejected with 404."""
    r = client.post(
        "/api/eval",
        json={"profile": trained_profile, "task": "recognition", "model_name": "nope"},
    )
    assert r.status_code == 404


def test_eval_result_404_before_worker_runs(
    client: TestClient, settings: Settings, trained_profile: str
) -> None:
    """GET result before the worker writes result.json returns 404."""
    model = _seed_model(settings)
    run_id = client.post(
        "/api/eval",
        json={"profile": trained_profile, "task": "recognition", "model_name": model},
    ).json()["run_id"]
    assert client.get(f"/api/eval/{run_id}/result").status_code == 404


def test_eval_round_trip(
    client: TestClient,
    settings: Settings,
    fake_runner: FakeLongJobRunner,
    trained_profile: str,
) -> None:
    """Acceptance (spec 07 §8): eval submission → result.json → API renders metrics."""
    from pdomain_ocr_trainer_spa.worker import evaluate as eval_worker

    model = _seed_model(settings)
    run_id = client.post(
        "/api/eval",
        json={"profile": trained_profile, "task": "recognition", "model_name": model},
    ).json()["run_id"]

    # Drive the eval worker in-process (the fake job runner does not spawn it).
    code = eval_worker.run_worker(
        settings.runs_dir / run_id, runner=_FakeEvalRunner()
    )
    assert code == 0
    assert (settings.runs_dir / run_id / "result.json").exists()

    # The API renders the metrics from result.json.
    result = client.get(f"/api/eval/{run_id}/result")
    assert result.status_code == 200
    body = result.json()
    assert body["overall"]["cer"] == 0.034
    assert body["overall"]["wer"] == 0.092
    assert body["sample_count"] == 1842

    # The markdown rendering is also available.
    md = client.get(f"/api/eval/{run_id}/result.md")
    assert md.status_code == 200
    assert "cer" in md.text.lower()
