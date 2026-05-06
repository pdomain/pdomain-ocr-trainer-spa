# 10 — Jobs and SSE

The job runner that owns every long-running operation
(training, eval, dataset publish, model publish, copy-to-datasets
batches over the threshold) and the SSE event stream that feeds
the SPA.

> Required reading: [`02-backend.md`](02-backend.md) §5.5,
> [`06-training-runs.md`](06-training-runs.md).
>
> Closely modelled on
> `pd-ocr-labeler-spa/specs/10-jobs-and-sse.md` and
> `pd-prep-for-pgdp/src/.../core/job_runner.py`. Where this spec is
> silent, those are authoritative.

---

## 1. Concept

A `Job` is the runtime container for a long-running operation. It
is decoupled from `Run` so we can reuse it for non-run operations
later (e.g. cache warm, asset migration) without polluting the
runs registry.

Every `Run` of `kind in {train, eval, publish-dataset,
publish-model}` has exactly one `Job`. Other operations (sync
copy-to-datasets) run inline if estimated < 30 s, else they spin a
`Job` of `kind="copy-to-datasets"` with `run_id=None`.

```python
class Job(BaseModel):
    id: str
    kind: str                    # "train.detection" | "train.recognition" | ... | "publish.dataset" | "publish.model" | "copy-to-datasets"
    run_id: str | None
    state: JobState              # see 01-data-models.md
    progress: JobProgress | None
    error: JobError | None
    started_at: datetime | None
    finished_at: datetime | None
```

---

## 2. JobRunner

```python
class JobRunner:
    """Owns the registry of jobs + the per-job event ring + the worker pool."""

    def submit(self, kind: str, fn: Callable[[Callable[[JobEvent], None], CancellationToken], None],
               run_id: str | None = None) -> Job: ...
    def get(self, job_id: str) -> Job: ...
    def list_active(self) -> list[Job]: ...
    def cancel(self, job_id: str) -> Job: ...
    def replay_buffer(self, job_id: str) -> list[JobEvent]: ...
    def stream(self, job_id: str) -> AsyncIterator[JobEvent]: ...
```

The runner uses an `asyncio.Queue` per job for live subscribers and
an in-memory ring (last 1000 events) for replay. Workers are
threads (so subprocess pipe reads don't block the event loop);
they post events into a queue that the FastAPI event loop
consumes via `asyncio.run_coroutine_threadsafe`.

For training jobs, `fn` is supplied by the
`ITrainingRunner.start(...)` adapter; the runner provides the
emit callback and a cancellation token.

Worker pool size: 1 for training jobs (one CUDA process at a time
by default — see [Q12](../OPEN_QUESTIONS.md)); unbounded for
publish + copy jobs (HTTP-bound, not GPU-bound).

---

## 3. JobEvent shape

```python
class JobEvent(BaseModel):
    """Tagged union over the wire."""
    type: Literal["log", "progress", "metric", "artefact", "complete", "failed", "cancelled", "heartbeat"]
    t: float                            # unix epoch with ms resolution
    # Log
    stream: Literal["stdout", "stderr"] | None = None
    line: str | None = None
    # Progress
    current: int | None = None
    total: int | None = None
    message: str | None = None
    # Metric
    name: str | None = None
    value: float | None = None
    step: int | None = None
    # Artefact
    path: str | None = None
    artefact_kind: Literal["weights", "config", "sidecar", "result", "preview"] | None = None
    # Failed
    code: str | None = None
    detail: dict | None = None
    # Complete
    exit_code: int | None = None
```

A discriminated union per JSON Schema; the OpenAPI export
materializes this so the SPA's `JobEvent` type is an exhaustive
union and `switch` on `type` is type-safe.

`heartbeat` events fire every 15 s when no other event has been
emitted in that window; they keep the SSE proxy alive on hosts
that idle-timeout dormant streams.

---

## 4. SSE protocol

```
GET /api/jobs/{job_id}/events
Accept: text/event-stream

retry: 5000

id: 1715035200123456
event: log
data: {"type":"log","t":1715035200.123,"stream":"stdout","line":"Epoch 1/100"}

id: 1715035200456789
event: progress
data: {"type":"progress","t":1715035200.456,"current":1,"total":100,"message":"epoch 1/100"}

...

id: 1715035500123456
event: complete
data: {"type":"complete","t":1715035500.123,"exit_code":0}
```

Conventions:

- Each event has a numeric `id:` (monotonic per-job, ms
  precision). Clients reconnect with `Last-Event-ID:` to resume.
- Server uses the `id` as a key into the per-job ring buffer for
  resume.
- One SSE `event:` name per `JobEvent.type`, mirroring the type.
- Default `retry:` = 5000 ms.

The frontend `subscribeToJob(jobId, on_event)` wrapper handles
reconnect and event-id restoration.

---

## 5. Buffering and retention

Each job has:

- **Live ring** in memory: last 1000 events. Lost on FastAPI
  restart.
- **Persistent log files** on disk:
  - `runs/<run_id>/stdout.log`, `stderr.log` (full text).
  - `runs/<run_id>/progress.jsonl` (only progress + metric +
    artefact events, capped at 50k lines per
    [`06-training-runs.md`](06-training-runs.md) §4).

On reconnect after a server restart, the SPA gets:

1. A 410 from `/events` (old job_id is gone).
2. Frontend falls back to polling `GET /api/runs/{run_id}` until
   status is terminal, while showing the on-disk
   `progress.jsonl` via `/api/runs/{run_id}/progress`.

This is intentional — keeping in-memory event rings across
restarts adds complexity for marginal value
([Q20](../OPEN_QUESTIONS.md): worth persisting?).

---

## 6. Cancellation

```
POST /api/jobs/{job_id}/cancel
→ 202 Job
```

Server flow:

1. `CancellationToken.requested = True`.
2. Worker observes the flag, signals the underlying operation
   (SIGTERM for subprocess, abort flag for HTTP upload).
3. Best-effort grace period (10 s for subprocess, 5 s for HTTP).
4. On terminal: emits `cancelled` event with truncate marker.

`POST /api/runs/{run_id}/cancel` is a thin wrapper that finds the
active job for the run and forwards.

---

## 7. Multi-tab fan-out

Multiple browser tabs subscribed to the same job ID share the
same upstream queue. The runner does not multi-cast at the
transport layer; each `stream()` is its own subscriber. Per-tab
queues are bounded (10000 events); slow consumers are dropped
with a sentinel `failed: backpressure` event after which the
client reconnects from `Last-Event-ID:`.

---

## 8. Active-job count endpoint

For the `JobsBadge` in the header bar:

```
GET /api/jobs/active-count
→ { "count": 1, "by_kind": {"train.recognition": 1} }
```

Polled at 5 s when count > 0, off otherwise.

---

## 9. Acceptance behaviour

1. Start a training run. Open three browser tabs on
   `/runs/{run_id}`. All three populate the LogViewer in real
   time, identical contents.
2. Restart the FastAPI server mid-run. The training subprocess is
   killed (TODO: detached or daemon? — [Q21](../OPEN_QUESTIONS.md)).
   On restart, the `Run` is marked failed with `process gone` per
   [`06-training-runs.md`](06-training-runs.md) §3.
3. Cancel a long-running publish job. SSE emits `cancelled`; the
   HTTP upload aborts within 5 s.
4. Disconnect a tab's network for 10 s. On reconnect, the SPA
   resumes from `Last-Event-ID:` and replays missed events.

---

## 10. Citations

- Job-runner pattern: `pd-ocr-labeler-spa/specs/10-jobs-and-sse.md`.
- Original: `pd-prep-for-pgdp/src/.../core/job_runner.py`.
- Subprocess + thread-pipe pattern: legacy `ui.py` training launch
  callbacks.
