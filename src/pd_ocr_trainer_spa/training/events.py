"""Parse the worker's @@PDEVENT@@ stdout protocol into pd-ocr-ops JobEvents.

The worker writes one line per pd-ocr-training TrainingEvent:

    @@PDEVENT@@ {"kind":"epoch","message":"...","progress":0.03,"data":{...}}

TrainingEvent.kind maps to JobEvent.kind (spec 02-backend §5.2):
    epoch / metric -> progress / metric
    log            -> log
    done / error   -> state
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

EVENT_PREFIX = "@@PDEVENT@@"

_KIND_MAP: dict[str, str] = {
    "log": "log",
    "epoch": "progress",
    "metric": "metric",
    "done": "state",
    "error": "state",
}


def is_event_line(line: str) -> bool:
    """True when ``line`` carries a structured @@PDEVENT@@ payload."""
    return line.lstrip().startswith(EVENT_PREFIX)


def parse_event_line(line: str, *, job_id: str, seq: int) -> dict[str, object]:
    """Parse one @@PDEVENT@@ line into a pd-ocr-ops JobEvent-shaped dict.

    Raises ValueError when the line is not a well-formed event line.
    """
    stripped = line.lstrip()
    if not stripped.startswith(EVENT_PREFIX):
        raise ValueError(f"not a @@PDEVENT@@ line: {line!r}")
    body = stripped[len(EVENT_PREFIX) :].strip()
    try:
        training_event: dict[str, object] = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed @@PDEVENT@@ payload: {body!r}") from exc

    training_kind = str(training_event.get("kind", ""))
    job_kind = _KIND_MAP.get(training_kind)
    if job_kind is None:
        raise ValueError(f"unknown TrainingEvent kind: {training_kind!r}")

    payload: dict[str, object] = {"message": training_event.get("message", "")}
    if training_event.get("progress") is not None:
        payload["progress"] = training_event["progress"]
    if training_event.get("data") is not None:
        payload["data"] = training_event["data"]
    if training_kind in {"done", "error"}:
        payload["state"] = "succeeded" if training_kind == "done" else "failed"

    return {
        "job_id": job_id,
        "seq": seq,
        "at": datetime.now(UTC).isoformat(),
        "kind": job_kind,
        "payload": payload,
    }
