r"""api/jobs.py — the SPA Job projection + SSE event stream (spec 10).

``pd-ocr-ops`` ``mount_routes`` exposes no job routes, so the SPA defines
``/api/jobs/*`` itself, wrapping the ``LongJobRunner``:

* ``GET  /api/jobs/{job_id}``         — project ``JobStatus`` onto ``Job``
* ``GET  /api/jobs/{job_id}/events``  — stream ``JobEvent``\ s as SSE
* ``POST /api/jobs/{job_id}/cancel``  — cancel; returns the terminal ``Job``
* ``GET  /api/jobs/active-count``     — non-terminal job count for the badge

The SPA owns no job runner; it only consumes the ``pd-ocr-ops`` contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pd_ocr_ops.gpu.local_jobs import UnknownJobError

from pd_ocr_trainer_spa.core.app_state import get_app_state
from pd_ocr_trainer_spa.core.enums import JobState
from pd_ocr_trainer_spa.core.errors import AppError
from pd_ocr_trainer_spa.core.models import Job

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from pd_ocr_ops.gpu.types import JobEvent, JobStatus

    from pd_ocr_trainer_spa.core.app_state import AppState

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

_TERMINAL: frozenset[JobState] = frozenset(
    {JobState.succeeded, JobState.failed, JobState.cancelled}
)
_SSE_RETRY_MS = 5000


def _job_not_found(job_id: str) -> AppError:
    """Build the canonical 404 for an unknown job_id."""
    return AppError(
        code="job.unknown",
        message=f"No job with id {job_id!r}",
        status_code=404,
    )


def _resolve_run_id(state: AppState, job_id: str) -> str | None:
    """Find the Run whose ``job_id`` matches, scanning the runs registry.

    ``run_id`` is not on ``JobStatus``; the SPA resolves it here. The runs
    registry is empty until the runs milestone, so this returns ``None``.
    """
    for run_id, run in state.runs.items():
        if getattr(run, "job_id", None) == job_id:
            return run_id
    return None


def _project(status: JobStatus, run_id: str | None) -> Job:
    """Project a pd-ocr-ops ``JobStatus`` onto the SPA ``Job`` model."""
    return Job(
        id=status.job_id,
        run_id=run_id,
        kind=status.kind,
        state=JobState(status.state),
        progress=status.progress,
        error=status.error,
        started_at=status.started_at,
        finished_at=status.finished_at,
    )


@router.get("/active-count")
async def active_count(
    state: AppState = Depends(get_app_state),
) -> dict[str, object]:
    """Return the count of non-terminal jobs, grouped by kind (spec 10 §8)."""
    runner = state.job_runner
    job_ids: list[str] = []
    introspect = getattr(runner, "all_job_ids", None)
    if callable(introspect):
        raw_ids: object = introspect()
        if isinstance(raw_ids, list):
            job_ids = [str(jid) for jid in cast("list[object]", raw_ids)]
    else:
        job_ids = [
            jid
            for jid in (getattr(run, "job_id", None) for run in state.runs.values())
            if jid is not None
        ]

    by_kind: dict[str, int] = {}
    for jid in job_ids:
        try:
            status = await runner.status(jid)
        except UnknownJobError:
            continue
        if JobState(status.state) in _TERMINAL:
            continue
        by_kind[status.kind] = by_kind.get(status.kind, 0) + 1

    return {"count": sum(by_kind.values()), "by_kind": by_kind}


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    state: AppState = Depends(get_app_state),
) -> Job:
    """Project ``LongJobRunner.status(job_id)`` onto the SPA ``Job`` model."""
    try:
        status = await state.job_runner.status(job_id)
    except UnknownJobError as exc:
        raise _job_not_found(job_id) from exc
    return _project(status, _resolve_run_id(state, job_id))


@router.post("/{job_id}/cancel", status_code=202)
async def cancel_job(
    job_id: str,
    state: AppState = Depends(get_app_state),
) -> Job:
    """Cancel a job; returns the terminal ``Job`` (no-op if already terminal)."""
    runner = state.job_runner
    try:
        await runner.cancel(job_id)
        status = await runner.status(job_id)
    except UnknownJobError as exc:
        raise _job_not_found(job_id) from exc
    return _project(status, _resolve_run_id(state, job_id))


def _sse_frame(event: JobEvent) -> str:
    """Serialize one ``JobEvent`` as an SSE frame (spec 10 §5)."""
    return (
        f"id: {event.seq}\n"
        f"event: {event.kind}\n"
        f"data: {event.model_dump_json()}\n\n"
    )


def _persist_progress(state: AppState, run_id: str | None, event: JobEvent) -> None:
    """Append a ``progress`` / ``metric`` event to the run's ``progress.jsonl``.

    Replay-safe: ``append_progress`` is keyed by the event ``seq`` upstream of
    de-dup; here we simply mirror live SSE events for chart replay (spec 06 §4).
    """
    if run_id is None or event.kind not in {"progress", "metric"}:
        return
    from pd_ocr_trainer_spa.domain.runs import append_progress

    record: dict[str, object] = {"type": event.kind, "seq": event.seq}
    record.update(event.payload)
    append_progress(state.settings, run_id, record)


async def _event_stream(
    state: AppState,
    job_id: str,
    last_event_id: int | None,
) -> AsyncIterator[str]:
    """Yield SSE frames for a job, honouring ``Last-Event-ID:`` replay skip."""
    runner = state.job_runner
    run_id = _resolve_run_id(state, job_id)
    yield f"retry: {_SSE_RETRY_MS}\n\n"
    # pd-ocr-ops Protocol-shape quirk: stream_events is declared `async def
    # -> AsyncIterator` but every impl is an async generator (directly
    # iterable). See docs/process/lint-deviations.md.
    async for event in runner.stream_events(job_id):  # pyright: ignore[reportGeneralTypeIssues]
        if last_event_id is None or event.seq > last_event_id:
            _persist_progress(state, run_id, event)
        if last_event_id is not None and event.seq <= last_event_id:
            continue
        yield _sse_frame(event)


@router.get("/{job_id}/events")
async def stream_job_events(
    job_id: str,
    request: Request,
    state: AppState = Depends(get_app_state),
) -> StreamingResponse:
    r"""Stream a job's ``JobEvent``\ s as Server-Sent Events (spec 10 §5).

    Validates the job exists up front so an unknown id is a 404 *before*
    the stream opens. Honours ``Last-Event-ID:`` by skipping events whose
    ``seq`` is ``<=`` the header value, replaying the rest from the runner's
    durable event log.
    """
    runner = state.job_runner
    try:
        await runner.status(job_id)
    except UnknownJobError as exc:
        raise _job_not_found(job_id) from exc

    header = request.headers.get("Last-Event-ID")
    last_event_id: int | None = None
    if header is not None:
        try:
            last_event_id = int(header)
        except ValueError:
            last_event_id = None

    return StreamingResponse(
        _event_stream(state, job_id, last_event_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
