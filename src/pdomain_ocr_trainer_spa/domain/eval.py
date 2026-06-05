"""Evaluation domain logic (spec 07-evaluation-and-metrics).

An eval is a :class:`Run` with ``kind="eval"`` — it reuses the ``runs/<id>/``
directory layout and the worker/job machinery. The distinguishing artefact is
``runs/<id>/result.json`` (the typed :class:`EvalResult`) plus a pretty
``result.md``.

This module is torch-free: it creates + validates the eval run and reads back
``result.json``. The eval worker subprocess (``worker/evaluate.py``) does the
actual model inference.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pdomain_ocr_trainer_spa.core.errors import AppError
from pdomain_ocr_trainer_spa.core.models import EvalResult, Run
from pdomain_ocr_trainer_spa.domain import models as model_dom
from pdomain_ocr_trainer_spa.domain import runs as run_dom
from pdomain_ocr_trainer_spa.domain.profiles import get_profile, normalize_profile_name

if TYPE_CHECKING:
    from pathlib import Path

    from pdomain_ocr_trainer_spa.core.enums import TaskEnum
    from pdomain_ocr_trainer_spa.settings import Settings


def _result_path(settings: Settings, run_id: str) -> Path:
    return run_dom.run_dir(settings, run_id) / "result.json"


def _result_md_path(settings: Settings, run_id: str) -> Path:
    return run_dom.run_dir(settings, run_id) / "result.md"


def default_val_source(settings: Settings, profile: str, task: TaskEnum) -> str:
    """Return the default local validation source for a (profile, task)."""
    del settings
    return f"local:ml-validation/{profile}/{task.value}"


def create_eval_run(
    settings: Settings,
    *,
    profile: str,
    task: TaskEnum,
    model_name: str,
    val_source: str | None = None,
    persist_predictions: bool = False,
    slice_glyph_features: bool = False,
    notes: str | None = None,
) -> Run:
    """Create an eval run: validate the model exists, write the run dir.

    Does not submit the worker job — ``api/eval.py`` owns the ``LongJobRunner``
    submission so the domain layer stays process-free.
    """
    normalized = normalize_profile_name(profile)
    get_profile(settings, normalized)  # 404 if the profile is unknown
    model_dom.get_model(settings, model_name)  # 404 if the model is unknown

    resolved_source = val_source or default_val_source(settings, normalized, task)
    args: dict[str, object] = {
        "model_name": model_name,
        "val_source": resolved_source,
        "persist_predictions": persist_predictions,
        "slice_glyph_features": slice_glyph_features,
    }

    run = Run(
        id=run_dom._new_run_id(),
        profile=normalized,
        task=task,
        kind="eval",
        status="pending",
        model_name=model_name,
        args=args,
        notes=notes,
        started_at=datetime.now(UTC),
    )

    rd = run_dom.run_dir(settings, run.id)
    rd.mkdir(parents=True, exist_ok=True)
    run_dom.write_manifest(settings, run)
    (rd / "args.json").write_text(json.dumps(args, indent=2), encoding="utf-8")
    (rd / "stdout.log").touch()
    (rd / "stderr.log").touch()
    (rd / "progress.jsonl").touch()
    return run


def write_result(settings: Settings, result: EvalResult) -> Path:
    """Persist an :class:`EvalResult` to ``runs/<id>/result.json`` + ``result.md``."""
    path = _result_path(settings, result.run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    _result_md_path(settings, result.run_id).write_text(render_result_markdown(result), encoding="utf-8")
    return path


def read_result(settings: Settings, run_id: str) -> EvalResult | None:
    """Read back ``runs/<id>/result.json`` as an :class:`EvalResult` (None if absent)."""
    path = _result_path(settings, run_id)
    if not path.exists():
        return None
    try:
        return EvalResult.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def get_result(settings: Settings, run_id: str) -> EvalResult:
    """Return one eval result, raising 404/409 per spec 07 §2."""
    run = run_dom.get_run(settings, run_id)
    if run.kind != "eval":
        raise AppError(
            code="eval.not_an_eval",
            message=f"Run {run_id!r} is not an eval run.",
            status_code=409,
        )
    if run.status in {"failed", "cancelled"}:
        raise AppError(
            code="eval.run_failed",
            message=f"Eval run {run_id!r} is {run.status}; no result available.",
            status_code=409,
        )
    result = read_result(settings, run_id)
    if result is None:
        raise AppError(
            code="eval.result_missing",
            message=f"Eval run {run_id!r} has not produced a result yet.",
            status_code=404,
        )
    return result


def render_result_markdown(result: EvalResult) -> str:
    """Render an :class:`EvalResult` as human-readable markdown (spec 07 §1)."""
    lines = [
        f"# Eval — {result.model_name}",
        "",
        f"- Profile: {result.profile}",
        f"- Task: {result.task.value}",
        f"- Validation source: {result.val_source}",
        f"- Samples: {result.sample_count}",
        f"- Duration: {result.duration_seconds:.1f}s",
        "",
        "## Overall metrics",
        "",
    ]
    overall = result.overall.model_dump(exclude_none=True)
    for key, value in overall.items():
        if key == "per_class":
            continue
        lines.append(f"- **{key}**: {value}")
    if result.slices:
        lines += ["", "## Slices", "", "| Feature | N pos | N neg | Δ CER |", "|---|---|---|---|"]
        for sl in result.slices:
            delta = "" if sl.delta_cer is None else f"{sl.delta_cer:+.4f}"
            lines.append(f"| {sl.feature} | {sl.n_pos} | {sl.n_neg} | {delta} |")
    return "\n".join(lines) + "\n"
