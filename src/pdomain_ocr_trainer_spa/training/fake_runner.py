"""Fake runner seams for CI (spec 14-testing §2.1, M12).

Two distinct seams live here:

* :class:`FakeLongJobRunner` — CI-safe ``LongJobRunner`` seam.  Emits a
  scripted sequence of pdomain-ops ``JobEvent`` objects and advances
  ``JobStatus.state`` through the lifecycle.  No subprocess, no GPU, no torch.

* :class:`FakeTrainingRunner` — CI-safe ``ITrainingRunner`` seam (M12 plan
  Task 2).  Implements ``train_detection``, ``train_recognition``, and
  ``train_typeface`` using scripted ``TrainingEvent`` streams so the worker
  dispatch path can be exercised without torch or DocTR.  Use this in tests
  that call ``_iter_events`` or ``run_worker`` directly.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pdomain_ops.gpu.local_jobs import UnknownJobError
from pdomain_ops.gpu.types import JobEvent, JobStatus

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

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

    def all_job_ids(self) -> list[str]:
        """Introspection seam — every registered job_id (for active-count).

        The pdomain-ops ``LongJobRunner`` Protocol has no enumeration method;
        ``api/jobs.py`` duck-types this when present. ``LocalLongJobRunner``
        gaining an equivalent is a documented M2 follow-up.
        """
        return list(self._jobs)

    async def status(self, job_id: str) -> JobStatus:
        """Return the current JobStatus, applying any scripted terminal state."""
        if job_id not in self._jobs:
            raise UnknownJobError(f"Job not found: {job_id!r}")
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
            raise UnknownJobError(f"Job not found: {job_id!r}")
        self._cancelled.add(job_id)
        self._jobs[job_id] = self._jobs[job_id].model_copy(
            update={"state": "cancelled", "finished_at": self._now()}
        )

    async def stream_events(self, job_id: str) -> AsyncIterator[JobEvent]:
        """Replay the scripted events until a terminal state (or cancellation)."""
        if job_id not in self._jobs:
            raise UnknownJobError(f"Job not found: {job_id!r}")
        for event in self._events.get(job_id, []):
            if job_id in self._cancelled:
                return
            yield event
            if event.kind == "state" and event.payload.get("state") in _TERMINAL:
                return


class FakeTrainingRunner:
    """CI-safe ITrainingRunner seam (M12 plan Task 2).

    Implements ``train_detection``, ``train_recognition``, and
    ``train_typeface`` with scripted ``TrainingEvent`` streams.  No torch, no
    DocTR, no GPU required.  Use in tests that exercise ``_iter_events`` or
    ``run_worker`` directly.
    """

    def train_detection(
        self,
        profile: str,
        config: object,
    ) -> Iterator[object]:
        """Fake detection training: 2 metric events then done."""
        from pdomain_ocr_training.protocols import TrainingEvent

        del profile, config
        for epoch in range(1, 3):
            yield TrainingEvent(
                kind="metric",
                message=f"epoch {epoch}",
                progress=epoch / 2,
                data={"f1": 0.80 + epoch * 0.05, "precision": 0.82, "recall": 0.79},
            )
        yield TrainingEvent(kind="done", message="training complete", progress=1.0)

    def train_recognition(
        self,
        profile: str,
        config: object,
    ) -> Iterator[object]:
        """Fake recognition training: 2 metric events then done."""
        from pdomain_ocr_training.protocols import TrainingEvent

        del profile, config
        for epoch in range(1, 3):
            yield TrainingEvent(
                kind="metric",
                message=f"epoch {epoch}",
                progress=epoch / 2,
                data={"cer": 0.10 - epoch * 0.02},
            )
        yield TrainingEvent(kind="done", message="training complete", progress=1.0)

    def train_typeface(
        self,
        profile: str,
        config: object,
    ) -> Iterator[object]:
        """Fake typeface-classification training: emits progress then done.

        Metric events carry ``accuracy`` and ``f1_macro`` so the worker can
        relay them to the frontend without torch.
        """
        from pdomain_ocr_training.protocols import TrainingEvent

        del profile, config
        for epoch in range(1, 4):
            yield TrainingEvent(
                kind="metric",
                message=f"epoch {epoch}",
                progress=epoch / 3,
                data={"accuracy": 0.80 + epoch * 0.05, "f1_macro": 0.78 + epoch * 0.05},
            )
        yield TrainingEvent(kind="done", message="training complete", progress=1.0)
