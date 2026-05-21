"""api/eval.py — model-evaluation REST surface (spec 07-evaluation-and-metrics §2).

Routes:

* ``POST /api/eval``                    — create + submit an eval run
* ``GET  /api/eval/{run_id}/result``    — the typed EvalResult
* ``GET  /api/eval/{run_id}/result.md`` — the pretty-printed markdown

An eval is a :class:`Run` with ``kind="eval"``; it reuses the run + job
machinery. The eval worker subprocess writes ``runs/<id>/result.json``.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Protocol, cast

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from pd_ocr_trainer_spa.core.app_state import get_app_state
from pd_ocr_trainer_spa.core.enums import TaskEnum  # noqa: TC001 — pydantic resolves at model-build time
from pd_ocr_trainer_spa.core.errors import AppError
from pd_ocr_trainer_spa.core.models import EvalResult  # noqa: TC001 — pydantic resolves at model-build time
from pd_ocr_trainer_spa.domain import eval as eval_dom
from pd_ocr_trainer_spa.domain import runs as run_dom

if TYPE_CHECKING:
    from pd_ocr_trainer_spa.core.app_state import AppState

router = APIRouter(prefix="/api/eval", tags=["eval"])


class _ProcessSubmitter(Protocol):
    """The ``submit_with_process`` seam (see ``api/runs.py`` for the rationale)."""

    async def submit_with_process(
        self, kind: str, spec: dict[str, object], cmd: list[str]
    ) -> str: ...


class EvalRequest(BaseModel):
    """Body for ``POST /api/eval`` (spec 07 §2)."""

    profile: str
    task: TaskEnum
    model_name: str
    val_source: str | None = None
    persist_predictions: bool = False
    slice_glyph_features: bool = False
    notes: str | None = None


class EvalResponse(BaseModel):
    """Response for ``POST /api/eval`` (``202 Accepted``)."""

    run_id: str
    job_id: str


def _build_eval_cmd(run_id: str, state: AppState) -> list[str]:
    """Return the argv for the eval worker subprocess."""
    run_dir = state.settings.runs_dir / run_id
    return [
        sys.executable,
        "-m",
        "pd_ocr_trainer_spa.worker.evaluate",
        "--run-dir",
        str(run_dir),
    ]


@router.post("", status_code=202)
async def create_eval(
    body: EvalRequest,
    state: AppState = Depends(get_app_state),
) -> EvalResponse:
    """Create an eval run, write its run dir, and submit the eval worker job."""
    settings = state.settings

    run = eval_dom.create_eval_run(
        settings,
        profile=body.profile,
        task=body.task,
        model_name=body.model_name,
        val_source=body.val_source,
        persist_predictions=body.persist_predictions,
        slice_glyph_features=body.slice_glyph_features,
        notes=body.notes,
    )

    cmd = _build_eval_cmd(run.id, state)
    submitter = cast("_ProcessSubmitter", cast("object", state.job_runner))
    job_id = await submitter.submit_with_process(
        kind=f"eval.{run.task.value}",
        spec={"run_id": run.id},
        cmd=cmd,
    )

    run = run_dom.mark_running(settings, run, job_id)
    state.runs[run.id] = run
    return EvalResponse(run_id=run.id, job_id=job_id)


@router.get("/{run_id}/result")
async def get_eval_result(
    run_id: str,
    state: AppState = Depends(get_app_state),
) -> EvalResult:
    """Return the typed EvalResult for a finished eval run (spec 07 §2)."""
    return eval_dom.get_result(state.settings, run_id)


@router.get("/{run_id}/result.md", response_class=PlainTextResponse)
async def get_eval_result_markdown(
    run_id: str,
    state: AppState = Depends(get_app_state),
) -> str:
    """Return the pretty-printed markdown for a finished eval run."""
    result = eval_dom.read_result(state.settings, run_id)
    if result is None:
        raise AppError(
            code="eval.result_missing",
            message=f"Eval run {run_id!r} has not produced a result yet.",
            status_code=404,
        )
    return eval_dom.render_result_markdown(result)
