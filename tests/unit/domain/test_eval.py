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
