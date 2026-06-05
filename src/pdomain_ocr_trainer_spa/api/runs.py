"""api/runs.py — training-run REST surface (spec 02 §5.4, spec 06).

Routes:

* ``POST   /api/runs``                 — create + submit a training run
* ``GET    /api/runs``                 — list runs (newest first)
* ``GET    /api/runs/{run_id}``        — one run
* ``POST   /api/runs/{run_id}/cancel`` — cancel a running run
* ``DELETE /api/runs/{run_id}``        — delete a terminal run
* ``GET    /api/runs/{run_id}/progress`` — progress.jsonl replay (chart)

The worker subprocess is owned by the pdomain-ops ``LongJobRunner``; this
router never imports torch.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Protocol, cast

from fastapi import APIRouter, Depends
from pdomain_ops.gpu.local_jobs import UnknownJobError
from pydantic import BaseModel

from pdomain_ocr_trainer_spa.core.app_state import get_app_state
from pdomain_ocr_trainer_spa.core.enums import TaskEnum  # noqa: TC001 — pydantic resolves at model-build time
from pdomain_ocr_trainer_spa.core.errors import AppError
from pdomain_ocr_trainer_spa.core.models import Run  # noqa: TC001 — pydantic resolves at model-build time
from pdomain_ocr_trainer_spa.domain import runs as dom
from pdomain_ocr_trainer_spa.training.worker_cmd import build_worker_cmd

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.core.app_state import AppState

router = APIRouter(prefix="/api/runs", tags=["runs"])


class _ProcessSubmitter(Protocol):
    """The ``submit_with_process`` seam.

    ``submit_with_process`` is implementation-specific (``LocalLongJobRunner``
    / ``FakeLongJobRunner``), not on the base ``LongJobRunner`` Protocol — the
    SPA's job runner is always one of those two, so the cast is sound.
    """

    async def submit_with_process(self, kind: str, spec: dict[str, object], cmd: list[str]) -> str: ...


class CreateRunRequest(BaseModel):
    """Body for ``POST /api/runs`` (spec 06 §2)."""

    profile: str
    task: TaskEnum
    args: dict[str, object] = {}
    notes: str | None = None
    device: int | None = None
    seed: int | None = None
    model_name: str | None = None
    qualifier: str | None = None


class CreateRunResponse(BaseModel):
    """Response for ``POST /api/runs`` (``202 Accepted``)."""

    run_id: str
    job_id: str


class RunListResponse(BaseModel):
    """Envelope for ``GET /api/runs``."""

    runs: list[Run]


def _train_job_running(state: AppState) -> bool:
    """True when any tracked run is still pending/running (one-train-job rule)."""
    return any(run.status in {"pending", "running"} for run in state.runs.values())


@router.post("", status_code=202)
async def create_run(
    body: CreateRunRequest,
    state: AppState = Depends(get_app_state),
) -> CreateRunResponse:
    """Create a training run, write its run dir, and submit the worker job.

    Concurrency: one ``train`` run at a time across the backend (D-T15).
    """
    settings = state.settings

    if _train_job_running(state):
        raise AppError(
            code="run.already_running",
            message="A training run is already in progress.",
            status_code=409,
        )

    run = dom.create_run(
        settings,
        profile=body.profile,
        task=body.task,
        args=body.args,
        notes=body.notes,
        device=body.device,
        seed=body.seed,
        model_name=body.model_name,
        qualifier=body.qualifier,
    )

    cmd = build_worker_cmd(run, settings)
    submitter = cast("_ProcessSubmitter", cast("object", state.job_runner))
    job_id = await submitter.submit_with_process(
        kind=f"train.{run.task.value}",
        spec={"run_id": run.id},
        cmd=cmd,
    )

    run = dom.mark_running(settings, run, job_id)
    state.runs[run.id] = run
    return CreateRunResponse(run_id=run.id, job_id=job_id)


@router.get("")
async def list_runs(
    state: AppState = Depends(get_app_state),
) -> RunListResponse:
    """List every run, newest first (spec 06 §8)."""
    runs = dom.list_runs(state.settings)
    for run in runs:
        state.runs[run.id] = run
    return RunListResponse(runs=runs)


@router.get("/{run_id}")
async def get_run(
    run_id: str,
    state: AppState = Depends(get_app_state),
) -> Run:
    """Return one run, refreshing its status from the owning job (spec 06 §7)."""
    run = dom.get_run(state.settings, run_id)
    run = await _reconcile_status(state, run)
    state.runs[run.id] = run
    return run


@router.post("/{run_id}/cancel", status_code=202)
async def cancel_run(
    run_id: str,
    state: AppState = Depends(get_app_state),
) -> Run:
    """Cancel a running run via ``LongJobRunner.cancel`` (spec 06 §3)."""
    settings = state.settings
    run = dom.get_run(settings, run_id)
    if run.status not in {"pending", "running"}:
        return run
    if run.job_id is not None:
        with contextlib.suppress(UnknownJobError):
            await state.job_runner.cancel(run.job_id)
    run = dom.mark_terminal(settings, run, status="cancelled", exit_code=None)
    state.runs[run.id] = run
    return run


@router.delete("/{run_id}", status_code=204)
async def delete_run(
    run_id: str,
    state: AppState = Depends(get_app_state),
) -> None:
    """Delete a terminal run (409 if running or artefacts exist)."""
    dom.delete_run(state.settings, run_id)
    state.runs.pop(run_id, None)


@router.get("/{run_id}/progress")
async def get_run_progress(
    run_id: str,
    state: AppState = Depends(get_app_state),
) -> dict[str, object]:
    """Return a run's ``progress.jsonl`` records for chart replay (spec 06 §4)."""
    dom.get_run(state.settings, run_id)  # 404 if absent
    return {"records": dom.read_progress(state.settings, run_id)}


async def _reconcile_status(state: AppState, run: Run) -> Run:
    """Refresh a non-terminal run's status from its owning job + progress log."""
    if run.status not in {"pending", "running"} or run.job_id is None:
        return run
    try:
        status = await state.job_runner.status(run.job_id)
    except UnknownJobError:
        return run

    job_state = str(status.state)
    if job_state in {"succeeded", "failed", "cancelled"}:
        return dom.mark_terminal(
            state.settings,
            run,
            status=job_state,
            exit_code=0 if job_state == "succeeded" else 1,
        )
    if job_state == "running" and run.status == "pending":
        return dom.update_run(state.settings, run, status="running")
    return run
