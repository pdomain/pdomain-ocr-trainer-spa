# 10 — Jobs and SSE

How the SPA observes every long-running operation (training, eval,
dataset publish, model publish) through the `pdomain-ocr-ops`
`LongJobRunner` and its SSE event stream.

> Required reading: [`02-backend.md`](02-backend.md) §5 / §6.5,
> [`06-training-runs.md`](06-training-runs.md).
>
> **Re-spec note (2026-05-21).** Rewritten onto the `pdomain-ocr-ops`
> `LongJobRunner` (D-T10, D-T20). The SPA no longer hand-rolls a
> `core/job_runner.py`, an asyncio event ring, or a worker pool —
> job lifecycle and event streaming are owned by `pdomain-ocr-ops`. This
> spec now describes how the SPA *consumes* that contract, not how
> it implements one.

---

## 1. Concept

A **job** is the runtime container for one long-running operation,
owned by the `pdomain-ocr-ops` `LongJobRunner`. Every `Run` of
`kind in {train, eval, publish-dataset, publish-model}` has exactly
one job; `Run.job_id` links them. Jobs exist only for long
operations — short dataset/profile mutations stay synchronous
request/response (the dataset kanban `apply` is synchronous, see
[`05-dataset-kanban.md`](05-dataset-kanban.md) §4).

The `LongJobRunner` is selected by `Settings.job_runner_kind`
(D-T20); core parity uses `LocalLongJobRunner`, a SQLite-backed
single-machine implementation.

---

## 2. The `LongJobRunner` contract (from `pdomain-ocr-ops`)

The SPA imports and depends on this Protocol — it does not define
it. `pdomain_ocr_ops.gpu` provides:

```python
class LongJobRunner(Protocol):                    # async, @runtime_checkable
    async def submit(self, kind: str, spec: dict[str, object]) -> str        # job_id
    async def status(self, job_id: str) -> JobStatus
    async def cancel(self, job_id: str) -> None
    async def stream_events(self, job_id: str) -> AsyncIterator[JobEvent]
```

`LocalLongJobRunner` additionally exposes
`submit_with_process(kind, spec, cmd: list[str]) -> job_id` — the
method the SPA uses for the training worker
([`02-backend.md`](02-backend.md) §5.1). It spawns and supervises an
OS subprocess; `cancel` is SIGTERM + grace + SIGKILL.

`JobStatus` — the poll/terminal shape:

```python
class JobStatus(BaseModel):              # extra="forbid"
    job_id: str
    kind: str
    state: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    progress: float = 0.0                # 0.0 ≤ v ≤ 1.0
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None                    # plain string; last stderr line on failure
```

`JobEvent` — one item in the event stream:

```python
class JobEvent(BaseModel):               # extra="forbid"
    job_id: str
    seq: int                             # monotonic per job, 1-based
    at: datetime
    kind: Literal["progress", "log", "state", "metric"]
    payload: dict[str, Any]              # kind-specific
```

`UnknownJobError(KeyError)` is raised by `status`, `cancel`, and
`stream_events` for an unknown `job_id`.

---

## 3. The SPA `Job` projection

`pdomain-ocr-ops` `mount_routes` exposes **no** job routes, so the SPA
defines `/api/jobs/*` itself (`api/jobs.py`), wrapping the runner.
`GET /api/jobs/{job_id}` projects a `JobStatus` onto the SPA `Job`
model that the frontend and OpenAPI export consume:

```python
class Job(BaseModel):
    id: str                              # = JobStatus.job_id
    kind: str                            # "train.detection" | "train.recognition"
                                         # | "eval" | "publish.dataset" | "publish.model"
    run_id: str | None                   # resolved from the Run registry by job_id
    state: JobState                      # = JobStatus.state (see 01-data-models.md)
    progress: float                      # = JobStatus.progress
    error: str | None                    # = JobStatus.error
    started_at: datetime | None
    finished_at: datetime | None
```

`run_id` is not on `JobStatus`; the SPA resolves it by scanning the
runs registry for the run whose `job_id` matches. `UnknownJobError`
→ `404 job.unknown`.

---

## 4. Job events on the wire

`payload` is kind-specific. The SPA serializes `JobEvent` verbatim
over SSE — it does **not** invent a parallel event model. Payload
shapes for training jobs (produced by the worker `@@PDEVENT@@`
protocol, [`02-backend.md`](02-backend.md) §5.2, and translated by
the `pdomain-ocr-ops` stdout parser — see [Q27](../OPEN_QUESTIONS.md)):

| `kind` | `payload` fields | Source |
|---|---|---|
| `progress` | `current: int`, `total: int`, `message: str` | training `epoch` event |
| `metric` | `name: str`, `value: float`, `step: int` | training `train_batch` / `val_batch` |
| `log` | `stream: "stdout" \| "stderr"`, `line: str` | any worker stdout/stderr line |
| `state` | `state: str`, `exit_code: int \| None`, `error: str \| None` | terminal `done` / `error` |

[`06-training-runs.md`](06-training-runs.md) §4 describes the same
events in a `type:`-keyed shorthand; the canonical wire shape is the
`pdomain-ocr-ops` `JobEvent` above (`kind` + `payload`).

A `state`-kind event is emitted on every state transition; the
final one carries the terminal `state`. There is no separate
`heartbeat` event — `LocalLongJobRunner.stream_events` polls every
`poll_interval_s` (default 0.5 s) and the SSE route emits an SSE
comment line as a keep-alive when no event has flowed for 15 s.

---

## 5. SSE protocol

```
GET /api/jobs/{job_id}/events
Accept: text/event-stream

retry: 5000

id: 1
event: progress
data: {"job_id":"j-abc","seq":1,"at":"2026-05-21T10:00:00Z","kind":"progress","payload":{"current":1,"total":100,"message":"epoch 1/100"}}

id: 2
event: log
data: {"job_id":"j-abc","seq":2,"at":"2026-05-21T10:00:01Z","kind":"log","payload":{"stream":"stdout","line":"..."}}

...

id: 142
event: state
data: {"job_id":"j-abc","seq":142,"at":"2026-05-21T10:05:00Z","kind":"state","payload":{"state":"succeeded","exit_code":0}}
```

`api/jobs.py` implements `GET /api/jobs/{job_id}/events` as a
`StreamingResponse` that `async for`s over
`LongJobRunner.stream_events(job_id)` and emits one SSE frame per
`JobEvent`:

- `id:` = `JobEvent.seq` (monotonic per job; clients reconnect with
  `Last-Event-ID:`).
- `event:` = `JobEvent.kind`.
- `data:` = the `JobEvent` JSON.
- `retry:` = 5000 ms.
- The stream closes after the terminal `state` event, or on
  `UnknownJobError` (→ 404 before the stream opens).

`stream_events` is itself event-id aware only to the extent that the
caller can pass a starting `seq`; the SPA route honours
`Last-Event-ID:` by skipping events with `seq ≤` the header value.

The frontend consumes this through the **pdomain-ui `useLongJob` hook**
(D-T19, D-T22) — the SPA does not hand-roll an `EventSource`
wrapper.

---

## 6. Buffering, retention, and restart

`LocalLongJobRunner` persists jobs and their events in a SQLite
database (`jobs` + `job_events` tables) at `Settings.jobs_db_path`.
This means:

- **Event replay** within a job's life: `stream_events` reads from
  `job_events` (every event ever written), so a reconnecting tab
  replays from `Last-Event-ID:` with no SPA-side ring buffer.
- **Across a FastAPI restart**: the SQLite registry survives, but
  the in-memory subprocess handles do not, and the training worker
  subprocess is a child of the dead FastAPI process (D-T3,
  [Q21](../OPEN_QUESTIONS.md)). So a job left `running` at boot is
  no longer truly running.

`AppState.hydrate_from_disk` reconciles at startup: any `Run` in
`running` whose job is not genuinely live is marked `failed`,
`exit_code = -1`, with a synthetic `stderr.log` line (D-T3). The SPA
does **not** attempt to reattach to orphaned subprocesses.

Persistent per-run artefacts (independent of the job registry):

- `runs/<run_id>/stdout.log`, `stderr.log` — full text.
- `runs/<run_id>/progress.jsonl` — `progress` + `metric` events,
  capped at 50k lines ([`06-training-runs.md`](06-training-runs.md)
  §4). Served by `GET /api/runs/{run_id}/progress` for chart replay
  of a finished or restart-orphaned run.

---

## 7. Cancellation

```
POST /api/jobs/{job_id}/cancel      → 202 Job
POST /api/runs/{run_id}/cancel      → 202 Run   (thin wrapper)
```

`api/jobs.py` calls `LongJobRunner.cancel(job_id)`. For a training
job that is `LocalLongJobRunner` SIGTERM → grace → SIGKILL on the
worker subprocess; job state → `cancelled`. `POST /api/runs/{run_id}
/cancel` resolves the run's active `job_id` and forwards.

Cancelling an already-terminal job is a no-op (returns the terminal
`Job`). Hard cancellation lives at the subprocess boundary because
`pdomain-ocr-training`'s `LocalTrainingRunner` has no in-process cancel
hook (D-T1).

---

## 8. Concurrency and the active-job count

One `train` job runs at a time across the backend (D-T15);
additional submissions sit `queued` in the `LongJobRunner` and start
FIFO. Publish jobs are HTTP-bound and not GPU-serialized.

For the header `JobsBadge`:

```
GET /api/jobs/active-count
→ { "count": 1, "by_kind": {"train.recognition": 1} }
```

`api/jobs.py` computes this by listing the runner's non-terminal
jobs. Polled at 5 s by the SPA when `count > 0`, off otherwise.

---

## 9. Multi-tab fan-out

Each browser tab opens its own `GET /api/jobs/{job_id}/events`
stream; each is an independent `stream_events` iterator over the
shared SQLite `job_events` table, so all tabs see identical
contents. There is no transport-layer multicast and no per-tab
backpressure sentinel — a slow tab simply lags its own SQLite
cursor.

---

## 10. Acceptance behaviour

1. Start a training run. Open three tabs on `/runs/{run_id}`. All
   three populate the LogViewer in real time with identical events.
2. Restart the FastAPI server mid-run. The worker subprocess dies
   with its parent; on restart the `Run` is marked `failed` with the
   `process gone` line (D-T3); `LossChart` still renders from
   `progress.jsonl`.
3. Cancel a running job via `POST /api/jobs/{id}/cancel`. The SSE
   stream emits a terminal `state` event with `state="cancelled"`.
4. Disconnect a tab's network for 10 s. On reconnect the SPA sends
   `Last-Event-ID:` and the route replays every `job_events` row
   with a higher `seq`.

---

## 11. Citations

- `LongJobRunner` Protocol / `JobStatus` / `JobEvent`:
  `pdomain-ocr-ops/pdomain_ocr_ops/gpu/protocols.py:27-45`,
  `pdomain-ocr-ops/pdomain_ocr_ops/gpu/types.py:25-56`.
- `LocalLongJobRunner` submit / supervise / cancel / stream:
  `pdomain-ocr-ops/pdomain_ocr_ops/gpu/local_jobs.py:64-272`.
- `mount_routes` exposes no job routes:
  `pdomain-ocr-ops/pdomain_ocr_ops/suite/routes.py:14`.
- Cross-repo stdout-parser dependency: [Q27](../OPEN_QUESTIONS.md),
  `pdomain/pdomain-ocr-ops#76`.
- Crash-recovery precedent:
  `pdomain-ocr-labeler-spa/specs/10-jobs-and-sse.md`.
