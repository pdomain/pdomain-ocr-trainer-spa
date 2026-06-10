"""Unit tests for domain/eval.py — eval run lifecycle (spec 07)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from pdomain_ocr_trainer_spa.core.enums import TaskEnum, TypefaceEnum
from pdomain_ocr_trainer_spa.core.errors import AppError
from pdomain_ocr_trainer_spa.core.models import EvalMetrics, EvalResult, ModelSidecar
from pdomain_ocr_trainer_spa.domain import eval as eval_dom
from pdomain_ocr_trainer_spa.domain.profiles import create_profile

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.settings import Settings


def _seed_model(settings: Settings) -> str:
    create_profile(
        settings,
        name="clogaelach",
        language="ga",
        typeface=TypefaceEnum.clogaelach,
    )
    name = "pd-ga-clogaelach-recognition-2026-05-05"
    leaf = settings.shared_models_dir / "clogaelach" / "recognition" / name
    leaf.mkdir(parents=True, exist_ok=True)
    (leaf / "model.pt").write_bytes(b"\x00")
    (leaf / f"{name}.metadata.json").write_text(ModelSidecar(name=name, task="recognition").model_dump_json())
    return name


def test_create_eval_run_writes_run_dir(settings: Settings) -> None:
    """create_eval_run creates a kind='eval' run with an args.json."""
    model = _seed_model(settings)
    run = eval_dom.create_eval_run(
        settings,
        profile="clogaelach",
        task=TaskEnum.recognition,
        model_name=model,
    )
    assert run.kind == "eval"
    assert run.args["model_name"] == model
    assert (settings.runs_dir / run.id / "args.json").exists()


def test_create_eval_run_unknown_model_404(settings: Settings) -> None:
    """An eval against a missing model raises 404."""
    create_profile(settings, name="clogaelach")
    with pytest.raises(AppError) as exc:
        eval_dom.create_eval_run(
            settings,
            profile="clogaelach",
            task=TaskEnum.recognition,
            model_name="nope",
        )
    assert exc.value.status_code == 404


def test_write_and_read_result_round_trip(settings: Settings) -> None:
    """write_result persists result.json + result.md; read_result round-trips."""
    model = _seed_model(settings)
    run = eval_dom.create_eval_run(
        settings,
        profile="clogaelach",
        task=TaskEnum.recognition,
        model_name=model,
    )
    result = EvalResult(
        run_id=run.id,
        profile="clogaelach",
        task=TaskEnum.recognition,
        model_name=model,
        val_source="local:ml-validation/clogaelach/recognition",
        overall=EvalMetrics(cer=0.034, wer=0.092),
        sample_count=1842,
        finished_at=datetime.now(UTC),
    )
    eval_dom.write_result(settings, result)
    assert (settings.runs_dir / run.id / "result.json").exists()
    assert (settings.runs_dir / run.id / "result.md").exists()
    back = eval_dom.read_result(settings, run.id)
    assert back is not None
    assert back.overall.cer == pytest.approx(0.034)


def test_get_result_missing_raises_404(settings: Settings) -> None:
    """get_result raises 404 before the eval worker has written a result."""
    model = _seed_model(settings)
    run = eval_dom.create_eval_run(
        settings,
        profile="clogaelach",
        task=TaskEnum.recognition,
        model_name=model,
    )
    with pytest.raises(AppError) as exc:
        eval_dom.get_result(settings, run.id)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# M12: typeface-classification eval
# ---------------------------------------------------------------------------


def _seed_typeface_model(settings: Settings) -> str:
    """Seed a typeface-classification model sidecar."""
    create_profile(
        settings,
        name="roman-test",
        language="en",
        typeface=TypefaceEnum.roman,
    )
    name = "pd-en-roman-typeface-classification-2026-06-10"
    leaf = settings.shared_models_dir / "roman-test" / "typeface-classification" / name
    leaf.mkdir(parents=True, exist_ok=True)
    (leaf / "model.pt").write_bytes(b"\x00")
    (leaf / f"{name}.metadata.json").write_text(
        ModelSidecar(name=name, task="typeface-classification").model_dump_json()
    )
    return name


def test_create_eval_run_typeface_creates_run_dir(settings: Settings) -> None:
    """create_eval_run accepts typeface-classification when model exists."""
    model = _seed_typeface_model(settings)
    run = eval_dom.create_eval_run(
        settings,
        profile="roman-test",
        task=TaskEnum.typeface_classification,
        model_name=model,
    )
    assert run.kind == "eval"
    assert run.task == TaskEnum.typeface_classification
    assert run.args["model_name"] == model
    assert (settings.runs_dir / run.id / "args.json").exists()


def test_eval_typeface_api_returns_202(settings: Settings, client: object) -> None:
    """POST /api/eval with typeface-classification task returns 202."""
    from fastapi.testclient import TestClient

    assert isinstance(client, TestClient)
    model = _seed_typeface_model(settings)
    resp = client.post(
        "/api/eval",
        json={
            "profile": "roman-test",
            "task": "typeface-classification",
            "model_name": model,
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "run_id" in data


def test_eval_typeface_result_round_trip(settings: Settings, client: object) -> None:
    """GET /api/eval/{id}/result returns typeface accuracy + f1_macro + per_class.

    Plan Task 5 acceptance: the round-trip through the fake seam for a
    typeface eval run.  The test writes an EvalResult with local per-class
    fields (accuracy, f1_macro, per_class as dict[str, ClassMetrics]) and
    verifies the API endpoint returns them correctly.
    """
    from fastapi.testclient import TestClient

    from pdomain_ocr_trainer_spa.core.models import ClassMetrics, EvalMetrics, EvalResult

    assert isinstance(client, TestClient)
    model = _seed_typeface_model(settings)

    # Create an eval run
    run = eval_dom.create_eval_run(
        settings,
        profile="roman-test",
        task=TaskEnum.typeface_classification,
        model_name=model,
    )

    # Simulate the eval worker writing a typeface result with per-class data
    per_class: dict[str, ClassMetrics] = {
        "roman": ClassMetrics(n=120, precision=0.95, recall=0.93, f1=0.94),
        "italic": ClassMetrics(n=80, precision=0.88, recall=0.91, f1=0.895),
    }
    result = EvalResult(
        run_id=run.id,
        profile="roman-test",
        task=TaskEnum.typeface_classification,
        model_name=model,
        val_source="local:ml-validation/roman-test/typeface-classification",
        overall=EvalMetrics(
            accuracy=0.923,
            f1_macro=0.917,
            per_class=per_class,
        ),
        sample_count=200,
        finished_at=datetime.now(UTC),
    )
    eval_dom.write_result(settings, result)
    # Mark run as running then succeeded so get_result doesn't 409
    from pdomain_ocr_trainer_spa.domain import runs as run_dom

    run = run_dom.mark_running(settings, run, "fake-job-id")
    run_dom.mark_terminal(settings, run, status="succeeded", exit_code=0)

    # Round-trip: GET /api/eval/{id}/result
    resp = client.get(f"/api/eval/{run.id}/result")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Overall typeface metrics
    overall = data["overall"]
    assert overall["accuracy"] == pytest.approx(0.923)
    assert overall["f1_macro"] == pytest.approx(0.917)
    assert "per_class" in overall
    per_class_resp = overall["per_class"]
    assert "roman" in per_class_resp
    assert "italic" in per_class_resp
    assert per_class_resp["roman"]["f1"] == pytest.approx(0.94)

    # Round-trip fields
    assert data["task"] == "typeface-classification"
    assert data["sample_count"] == 200
