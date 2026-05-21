"""FakeLongJobRunner — the CI-safe LongJobRunner seam (spec 14-testing §2.1).

Instead of spawning a worker subprocess, it emits a scripted sequence of
pd-ocr-ops JobEvents and advances JobStatus.state through the lifecycle.
No subprocess, no GPU, no torch.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pd_ocr_ops.gpu.types import JobEvent, JobStatus

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

_TERMINAL = {"succeeded", "failed", "cancelled"}


class FakeLongJobRunner:
    """In-test LongJobRunner: scripted events, no real process.

    Set ``script`` to a list of JobEvents (job_id / seq / at are filled in by
    the fake) before submitting. ``submit`` and ``submit_with_process`` both
    register a job and replay the script.
    """

    def __init__(self) -> None:
        self.script: list[JobEvent] = []
        self._jobs: dict[str, JobStatus] = {}
        self._events: dict[str, list[JobEvent]] = {}
        self._cancelled: set[str] = set()

    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _register(self, kind: str) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = JobStatus(
            job_id=job_id,
            kind=kind,
            state="running",
            progress=0.0,
            started_at=self._now(),
        )
        self._events[job_id] = self._materialize_script(job_id)
        return job_id

    def _materialize_script(self, job_id: str) -> list[JobEvent]:
        events: list[JobEvent] = []
        for seq, template in enumerate(self.script):
            events.append(
                JobEvent(
                    job_id=job_id,
                    seq=seq,
                    at=self._now(),
                    kind=template.kind,
                    payload=dict(template.payload),
                )
            )
        return events

    async def submit(self, kind: str, spec: dict[str, object]) -> str:
        """Register a job; returns the job_id."""
        del spec
        return self._register(kind)

    async def submit_with_process(
        self,
        kind: str,
        spec: dict[str, object],
        cmd: list[str],
    ) -> str:
        """Register a job (no real subprocess is launched in the fake)."""
        del spec, cmd
        return self._register(kind)

    async def status(self, job_id: str) -> JobStatus:
        """Return the current JobStatus, applying any scripted terminal state."""
        status = self._jobs[job_id]
        if job_id in self._cancelled:
            return status
        for event in self._events.get(job_id, []):
            if event.kind == "state":
                state = str(event.payload.get("state", status.state))
                status = status.model_copy(
                    update={"state": state, "progress": 1.0, "finished_at": self._now()}
                )
        self._jobs[job_id] = status
        return status

    async def cancel(self, job_id: str) -> None:
        """Flip the job to a cancelled terminal state and suppress later events."""
        if job_id not in self._jobs:
            return
        self._cancelled.add(job_id)
        self._jobs[job_id] = self._jobs[job_id].model_copy(
            update={"state": "cancelled", "finished_at": self._now()}
        )

    async def stream_events(self, job_id: str) -> AsyncIterator[JobEvent]:
        """Replay the scripted events until a terminal state (or cancellation)."""
        for event in self._events.get(job_id, []):
            if job_id in self._cancelled:
                return
            yield event
            if event.kind == "state" and event.payload.get("state") in _TERMINAL:
                return
