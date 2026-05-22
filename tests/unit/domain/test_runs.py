"""Unit tests for domain/runs.py — run lifecycle, persistence, crash recovery."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from pd_ocr_trainer_spa.core.enums import TaskEnum, TypefaceEnum
from pd_ocr_trainer_spa.core.errors import AppError
from pd_ocr_trainer_spa.domain import runs as dom
from pd_ocr_trainer_spa.domain.profiles import create_profile

if TYPE_CHECKING:
    from pd_ocr_trainer_spa.settings import Settings


def _seed_profile(settings: Settings, *, with_data: bool = True) -> str:
    create_profile(
        settings,
        name="clogaelach",
        language="ga",
        typeface=TypefaceEnum.clogaelach,
    )
    if with_data:
        task_dir = settings.ml_training_dir / "clogaelach" / "recognition"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "labels.json").write_text(
            json.dumps({"crop-1": "label"}), encoding="utf-8"
        )
    return "clogaelach"


def test_derive_model_name_uses_language_typeface_task_date(settings: Settings) -> None:
    _seed_profile(settings)
    name = dom.derive_model_name(
        settings, profile="clogaelach", task=TaskEnum.recognition
    )
    assert name.startswith("pd-ga-clogaelach-recognition-")


def test_derive_model_name_blocks_incomplete_profile(settings: Settings) -> None:
    create_profile(settings, name="bare")  # no language / typeface
    with pytest.raises(AppError) as exc:
        dom.derive_model_name(settings, profile="bare", task=TaskEnum.recognition)
    assert exc.value.code == "run.profile_incomplete"


def test_create_run_writes_run_dir(settings: Settings) -> None:
    _seed_profile(settings)
    run = dom.create_run(
        settings, profile="clogaelach", task=TaskEnum.recognition, args={"epochs": 5}
    )
    rd = dom.run_dir(settings, run.id)
    assert (rd / "manifest.json").exists()
    assert (rd / "args.json").exists()
    assert (rd / "stdout.log").exists()
    assert (rd / "progress.jsonl").exists()
    assert run.status == "pending"
    assert run.model_name.startswith("pd-ga-clogaelach-recognition-")


def test_create_run_rejects_empty_training_data(settings: Settings) -> None:
    _seed_profile(settings, with_data=False)
    with pytest.raises(AppError) as exc:
        dom.create_run(settings, profile="clogaelach", task=TaskEnum.recognition, args={})
    assert exc.value.code == "run.no_training_data"


def test_create_run_rejects_unsupported_task(settings: Settings) -> None:
    _seed_profile(settings)
    with pytest.raises(AppError) as exc:
        dom.create_run(
            settings,
            profile="clogaelach",
            task=TaskEnum.glyph_classification,
            args={},
        )
    assert exc.value.code == "run.task_unsupported"


def test_prepare_worker_args_fills_paths(settings: Settings) -> None:
    _seed_profile(settings)
    run = dom.create_run(
        settings, profile="clogaelach", task=TaskEnum.recognition, args={"epochs": 3}
    )
    args = json.loads(
        (dom.run_dir(settings, run.id) / "args.json").read_text(encoding="utf-8")
    )
    assert args["epochs"] == 3
    assert args["train_path"].endswith("clogaelach/recognition")
    assert args["val_path"].endswith("clogaelach/recognition")
    assert args["output_dir"].endswith("artefacts")
    assert args["name"] == run.model_name


def test_manifest_round_trip(settings: Settings) -> None:
    _seed_profile(settings)
    run = dom.create_run(
        settings, profile="clogaelach", task=TaskEnum.recognition, args={}
    )
    reloaded = dom.read_manifest(settings, run.id)
    assert reloaded is not None
    assert reloaded.id == run.id
    assert reloaded.model_name == run.model_name


def test_progress_append_and_read(settings: Settings) -> None:
    _seed_profile(settings)
    run = dom.create_run(
        settings, profile="clogaelach", task=TaskEnum.recognition, args={}
    )
    dom.append_progress(settings, run.id, {"type": "progress", "current": 1, "total": 3})
    dom.append_progress(settings, run.id, {"type": "metric", "name": "val_cer"})
    records = dom.read_progress(settings, run.id)
    assert len(records) == 2
    assert records[0]["type"] == "progress"
    assert "t" in records[0]


def test_list_runs_newest_first(settings: Settings) -> None:
    _seed_profile(settings)
    first = dom.create_run(
        settings, profile="clogaelach", task=TaskEnum.recognition, args={}
    )
    second = dom.create_run(
        settings, profile="clogaelach", task=TaskEnum.recognition, args={}
    )
    runs = dom.list_runs(settings)
    ids = [r.id for r in runs]
    assert ids[0] == second.id
    assert first.id in ids


def test_get_run_unknown_404(settings: Settings) -> None:
    with pytest.raises(AppError) as exc:
        dom.get_run(settings, "nonexistent")
    assert exc.value.code == "run.unknown"


def test_delete_run_refuses_running(settings: Settings) -> None:
    _seed_profile(settings)
    run = dom.create_run(
        settings, profile="clogaelach", task=TaskEnum.recognition, args={}
    )
    with pytest.raises(AppError) as exc:
        dom.delete_run(settings, run.id)
    assert exc.value.code == "run.not_terminal"


def test_delete_run_removes_terminal(settings: Settings) -> None:
    _seed_profile(settings)
    run = dom.create_run(
        settings, profile="clogaelach", task=TaskEnum.recognition, args={}
    )
    dom.mark_terminal(settings, run, status="succeeded", exit_code=0)
    dom.delete_run(settings, run.id)
    assert not dom.run_dir(settings, run.id).exists()


# ---------------------------------------------------------------------------
# M10 — HF source references in run args
# ---------------------------------------------------------------------------


def test_create_run_accepts_hf_source_in_args(settings: Settings) -> None:
    """A run created with an HF source in args.sources stores it in manifest."""
    _seed_profile(settings)
    hf_source = {"kind": "huggingface", "repo": "ntw8532/pd-ocr-synth-ga-clogaelach", "revision": "main", "weight": 1.0}
    run = dom.create_run(
        settings,
        profile="clogaelach",
        task=TaskEnum.recognition,
        args={"epochs": 2, "sources": [hf_source]},
    )
    assert run.args["sources"] == [hf_source]

    # manifest round-trips the sources
    reloaded = dom.read_manifest(settings, run.id)
    assert reloaded is not None
    reloaded_sources = reloaded.args.get("sources", [])
    assert len(reloaded_sources) == 1
    assert reloaded_sources[0]["repo"] == "ntw8532/pd-ocr-synth-ga-clogaelach"


def test_prepare_worker_args_preserves_hf_source(settings: Settings) -> None:
    """prepare_worker_args forwards the HF source entry to the worker args.json."""
    _seed_profile(settings)
    hf_source = {"kind": "huggingface", "repo": "ntw8532/test-ds", "revision": "main", "weight": 0.7}
    run = dom.create_run(
        settings,
        profile="clogaelach",
        task=TaskEnum.recognition,
        args={"epochs": 1, "sources": [hf_source]},
    )
    args = json.loads(
        (dom.run_dir(settings, run.id) / "args.json").read_text(encoding="utf-8")
    )
    # The HF source must be passed through to the worker for materialization.
    sources = args.get("sources", [])
    assert len(sources) == 1
    assert sources[0]["repo"] == "ntw8532/test-ds"
