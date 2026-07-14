# 06 — Training runs

How the SPA starts, monitors, and finishes a training run. Detection,
recognition, typeface-classification, and glyph-classification share
this surface; per-task differences are §5.

> Required reading: [`01-data-models.md`](01-data-models.md) §3,
> [`02-backend.md`](02-backend.md) §4.3 / §5 / §6.4 / §6.5,
> [`04-profiles-and-config.md`](04-profiles-and-config.md) §3,
> [`10-jobs-and-sse.md`](10-jobs-and-sse.md).
>
> **Re-spec note (2026-05-21).** Rewritten onto the
> `pdomain-ocr-training` + `pdomain-ocr-ops` stack (D-T1, D-T20). A training
> run now drives `pdomain-ocr-training`'s `ITrainingRunner` inside a
> worker subprocess supervised by the `pdomain-ocr-ops` `LongJobRunner`.
> The original raw-`pdomain-ocr-training` subprocess and the per-task
> stdout regex parser are superseded — progress now arrives as
> structured `TrainingEvent`s, not parsed log lines.

---

## 1. Lifecycle

```
[click Start]
   │
   ▼
POST /api/runs ─────────► server: write runs/<id>/{manifest,args}.json
   │                       build worker argv (training/worker_cmd.py)
   │                       LongJobRunner.submit_with_process(kind, spec, cmd)
   │                       create Run, link Run.job_id = job_id
   ◄── 202 {run_id, job_id}
   │
   ▼
EventSource /api/jobs/{job_id}/events     (SSE; backed by LongJobRunner.stream_events)
   │
   │   event: log       data: { "type":"log","stream":"stdout","line":"..." }
   │   event: progress  data: { "type":"progress","current":3,"total":100,"message":"epoch 3/100" }
   │   event: metric    data: { "type":"metric","name":"val_cer","value":0.045,"step":3 }
   │   event: state     data: { "type":"complete","exit_code":0 } | { "type":"failed","code":"..." }
   ▼
SSE close
   │
   ▼
queryClient.invalidate(["run", run_id])
```

A run is owned end-to-end by one `LongJobRunner` job. The job
registry is SQLite-backed and survives a FastAPI restart, but the
worker subprocess does not — reload-mid-run reattaches by re-opening
`GET /api/jobs/{job_id}/events`; reconnect-after-server-restart falls
back to on-disk `progress.jsonl` (D-T3, D-T10). The job/SSE transport
contract is [`10-jobs-and-sse.md`](10-jobs-and-sse.md).

---

## 2. Creating a run

`POST /api/runs` body:

```python
class CreateRunRequest(BaseModel):
    profile: str
    task: TaskEnum
    kind: Literal["train"] = "train"     # eval and publish go through their own endpoints
    args: dict                            # task-specific; see 04-profiles-and-config.md §3.2
    sources: list[DatasetSourceRef] | None = None   # default: one local source for this profile+task

    # Optional overrides
    device: int | None = None             # GPU index; None = pdomain-ocr-training default device
    seed: int | None = None
    notes: str | None = None              # free-form, persisted in manifest.json
    model_name: str | None = None         # if absent, derived via §6
```

Response (`202 Accepted`):

```python
class CreateRunResponse(BaseModel):
    run_id: str
    job_id: str
    eta_seconds: int | None              # very rough; computed from last completed run of same shape
```

Validation:

- `task` must be enabled (`Settings.enable_typeface_training`,
  `Settings.enable_glyph_training` for the new tasks).
- `args` must validate against the task's `pdomain-ocr-training` config
  model (`DetectionConfig` / `RecognitionConfig` — both `extra`-
  forbidding pydantic models, so unknown keys are `422` with
  field-level errors).
- `sources` must all exist; for a `local` source, the
  `<ml_training_dir>/<profile>/<task>/` dir must contain a
  `labels.json` with at least one entry (`409 run.no_training_data`).
- Concurrency: one `train` job runs at a time across the backend
  (D-T15); further submissions queue in the `LongJobRunner` and start
  FIFO. See the
  [trainer workflow architecture](../docs/architecture/trainer-workflows.md).

Side effects:

- `runs/<id>/` directory created; `manifest.json`, `args.json` written.
- `Run.status = "pending"` → `running` once the `LongJobRunner` job
  state reports `running`.
- Notification toast: "Training started — '<model_name>'" with link
  to `/runs/{run_id}`.

`args` is validated against the typed config but **not** itself the
config — `training/config_build.py` maps `args` onto a
`DetectionConfig` / `RecognitionConfig` inside the worker. For
recognition, `config_build` resolves `vocab_library` +
`custom_characters` into the final `vocab` string
(`"CUSTOM:<chars>"` or a named DocTR vocab).

---

## 3. The training worker subprocess

The run executes as the worker subprocess specified in
[`02-backend.md`](02-backend.md) §5. Recap of the run-relevant
behaviour:

```
python -m pdomain_ocr_trainer_spa.worker.train --run-dir runs/<id>
```

The worker:

1. Reads `runs/<id>/{manifest,args}.json`.
2. Builds the typed config (`training/config_build.py`).
3. Sets process env from the manifest: `HF_HOME`,
   `CUDA_VISIBLE_DEVICES` filtered to the chosen `device`, and the
   legacy `PD_OCR_TRAINER_ML_TRAINING_DIR` / `..._ML_VALIDATION_DIR`
   that `pdomain_ocr_training.datasets` reads at import.
4. Instantiates `pdomain_ocr_training.LocalTrainingRunner` and **fully
   drains** `train_detection(profile, cfg)` /
   `train_recognition(profile, cfg)` — the iterator must be consumed
   to completion; abandoning it strands the in-process training
   thread and the GPU.
5. Emits one `@@PDEVENT@@ {json}` stdout line per `TrainingEvent`
   (§4), mirrors `message` to `runs/<id>/stdout.log`, and lets raw
   stderr flow to `runs/<id>/stderr.log`.
6. Exits `0` after the `done` event, non-zero after `error`.

The `pdomain-ocr-ops` `LongJobRunner` owns this subprocess: `submit_with_
process` spawns and supervises it; `cancel(job_id)` terminates it.

Cancellation:

1. `POST /api/runs/{run_id}/cancel` → `LongJobRunner.cancel(job_id)`.
2. The runner sends SIGTERM, waits a grace period, then SIGKILL.
3. Job state → `cancelled`; the SPA flips `Run.status` to `cancelled`.

Hard cancellation lives at the *process* boundary because
`LocalTrainingRunner` has **no in-process cancellation hook** — this
is the primary reason training is isolated in a subprocess (D-T1).

Crash recovery:

- If the FastAPI process dies mid-run, on next boot
  `AppState.hydrate_from_disk` finds the `Run` in `running` with no
  live job and marks it `failed`, `exit_code = -1`, appending
  `"[trainer-spa] process gone before exit; marked failed at boot"`
  to `stderr.log` (D-T3).

---

## 4. Progress + metric events

`pdomain-ocr-training` already emits **structured** `TrainingEvent`s — the
SPA does **not** regex-parse log lines. Each `TrainingEvent` has:

```python
kind: Literal["log", "epoch", "metric", "done", "error"]
message: str
progress: float | None       # normalized [0,1]; set on `epoch` events
data: dict | None             # loss / lr / batch / recall / ... per kind
```

How each `kind` arises (from `pdomain-ocr-training`'s raw→public mapping):

| `kind`  | Source | Carries |
|---|---|---|
| `epoch`  | `epoch_end` | `progress = epoch / total_epochs`; `data` = epoch-end fields |
| `metric` | `train_batch` / `val_batch` | `message` = `train/val batch N/total`; `data` = `loss`, `lr`, `batch`, `total_batches` |
| `log`    | raw `log` + any unknown raw kind | `message` only |
| `done`   | synthesized terminal | `message = "Training completed successfully."` |
| `error`  | synthesized terminal | `message = "<ExcType>: <msg>\n<traceback>"` |

The worker serializes each event to a `@@PDEVENT@@`-prefixed stdout
JSON line. The `pdomain-ocr-ops` `LongJobRunner` parses those lines into
`JobEvent`s surfaced by `stream_events(job_id)`; the SPA SSE route
(`/api/jobs/{job_id}/events`) re-emits them. `kind` mapping to the
SPA wire `JobEvent.type`:

- `epoch` → `progress` (`current`/`total` derived from `progress` ×
  the run's epoch count, `message` passthrough)
- `metric` → one `metric` event per numeric value in `data`
- `log` → `log`
- `done` → `complete` (`exit_code: 0`)
- `error` → `failed` (`code` mapped per §9)

The server appends `progress` + `metric` events to
`runs/<id>/progress.jsonl` for replay and chart rendering. The
frontend `LossChart` reads `progress.jsonl` via
`GET /api/runs/{run_id}/progress` for an old run, and consumes the
SSE stream directly while a run is live.

`progress.jsonl` shape per line:

```json
{"t": 1715035200.123, "type": "progress", "current": 3, "total": 100, "message": "..."}
{"t": 1715035200.456, "type": "metric", "name": "val_cer", "value": 0.045, "step": 3}
```

Cap: 50k events per run on disk; older are GC'd oldest-first once the
file hits the cap. See the
[deferred progress-cap review](../docs/context/intent-map.md).

> Because `TrainingEvent`s are typed at the source, the legacy
> regex `training.parser_drift` failure mode is retired — the only
> remaining "no progress" case is a worker that never reaches its
> first `epoch` event, surfaced as `training.import_error` /
> `training.worker_died` per §9. See the
> [rejected regex-parser threshold](../docs/context/intent-map.md).

---

## 5. Per-task differences

### 5.1 Detection

- Config: `DetectionConfig`
  ([`04-profiles-and-config.md`](04-profiles-and-config.md) §3.2) —
  `arch="db_resnet50"`, `epochs=100`, `batch_size=2`, `rotation` for
  rotated-bbox polygons.
- Required dataset: `<ml_training_dir>/<profile>/detection/labels.json`.
- Artefact: `<model_name>.pt` + sidecar, written by the worker into
  `config.output_dir`.

### 5.2 Recognition

- Config: `RecognitionConfig` — `arch="crnn_vgg16_bn"`, `epochs=10`,
  `batch_size=64`, `vocab` a plain `str`.
- `config_build.py` resolves `vocab_library` + `custom_characters`
  into `RecognitionConfig.vocab` — a named DocTR vocab or the literal
  `"CUSTOM:<chars>"` — before the worker is launched.
- The "scan training set for missing chars" button on the run form
  hits `POST /api/profiles/{p}/scan-missing-chars` (see
  [`04-profiles-and-config.md`](04-profiles-and-config.md) §2.3) and
  inlines the response into the form's `custom_characters` field.

### 5.3 Typeface classification (M (a.5))

- Reads `<ml_training_dir>/<profile>/typeface/metadata.jsonl`.
- Architecture remains blocked upstream (see the
  [intent map](../docs/context/intent-map.md)); config model is a
  future `pdomain-ocr-training` addition.
- `metric`-kind events carry `accuracy`, `f1_macro`, per-class
  accuracy in `data`.

### 5.4 Glyph classification (g2)

- Reads `<ml_training_dir>/<profile>/glyph/metadata.jsonl`.
- Multi-head sigmoid; one head per feature in `feature_heads`.
- Per-feature precision / recall surface as separate `metric` events.
- Eval gate: per-feature precision ≥ 0.99 for "auto-fill", recall
  ≥ 0.9 for "suggest" — mirrors `pdomain-ocr-training/docs/ROADMAP.md` (g2).

---

## 6. Model name derivation

Default `model_name` is computed at create-run time:

```
pd-{language}-{typeface}-{task}-{date}[-{qualifier}]
```

- `language`, `typeface` from the profile's `profile.toml`. If
  either is unset, the SPA blocks the run with an inline form error
  ("Set language + typeface on this profile before training, or
  enter an explicit Model name override.").
- `task` ∈ `detection | recognition | typeface-classification | glyph-classification`.
- `date` = `YYYY-MM-DD` (UTC).
- Optional `qualifier` from a free-form input on the run form.
- Legacy form (`pd-{profile}-{task}-...`) is read/evaluated but never
  minted; it is accepted only as an explicit `model_name` override
  the user types (D-T6).

The derived name becomes `config.name` (the `pdomain-ocr-training`
checkpoint stem). The frontend `lib/modelName.ts` parses + renders
both shapes for display.

---

## 7. Run-detail page

Route: `/runs/{run_id}`.

Layout:

```
┌─────────────────────────────────────────────────────────────────┐
│ <breadcrumb> · Profile · Task · model_name · JobStatusPip       │
├──────────────────────────────────────────────┬──────────────────┤
│ LossChart (recharts; train/val curves)       │  Sidebar         │
│                                              │  - Args summary  │
│                                              │  - Progress      │
│                                              │  - ETA           │
│                                              │  - Sources       │
│                                              │  - Artefacts     │
├──────────────────────────────────────────────┴──────────────────┤
│ LogViewer  [stdout|stderr toggle] [auto-scroll] [wrap] [copy]   │
│  ▼ thousands of lines, virtualized                              │
└─────────────────────────────────────────────────────────────────┘
```

`JobStatusPip`, `Progress`, and the `LogViewer` are **pdomain-ui
components** driven by the `useLongJob` SSE hook (D-T4, D-T19,
D-T22); `LossChart` is the SPA's only app-specific chart.

Actions:

- `[Cancel]` (only when `status == running`) → `POST /api/runs/{id}/cancel`.
- `[Resume from checkpoint]` — disabled for v1; placeholder.
- `[Open Model]` (only when `status == succeeded` and an artefact
  is registered).
- `[Open Eval]` — opens a prefilled eval form against this model.
- `[Delete run]` (only when `status` terminal; refuses if artefacts
  exist on disk).

---

## 8. Run-list page

Route: `/runs`.

- Table: started_at | profile | task | kind | status | duration | model_name (link).
- Filters: profile (multi), task (multi), status (multi), kind (multi).
- Paginated (server-side); infinite-scroll.
- Status badge / `JobStatusPip` colour: pending=grey, running=blue,
  succeeded=green, failed=red, cancelled=amber.
- Click row → `/runs/{run_id}`.

---

## 9. Failure surfacing

Failure modes map to error codes in
[`02-backend.md`](02-backend.md) §7 / [`11-notifications.md`](11-notifications.md).
A `TrainingEvent` of `kind="error"` carries `<ExcType>: <msg>` in
`message`; `training/events.py` classifies it into a stable code:

| Error code | Trigger | UI surface |
|---|---|---|
| `training.cuda_oom` | OOM exception type / keyword in the `error` event | Toast + sidebar warning + "Reduce batch size" link to clone+edit run. |
| `training.no_training_data` | Empty `labels.json` detected at create-run validation | Form-level error before submit; never reaches the worker. |
| `training.cuda_unavailable` | Worker fails to acquire the requested GPU device | Form warning if `device` is unset; outright error if a device was pinned. |
| `training.import_error` | Worker exits non-zero before the first `@@PDEVENT@@` line | Run goes `failed`; sidebar shows captured `stderr.log` verbatim. |
| `training.worker_died` | Worker thread died without an error sentinel (`pdomain-ocr-training` emits `"Worker thread died without reporting an error."`) | Run `failed`; sidebar shows the message. |

---

## 10. Acceptance behaviour

1. Configure recognition defaults for the `clogaelach` profile.
   Click "New run". Form prefills from defaults. Override `epochs`
   to 5 for a smoke test. Click Start.
2. Within 1 s the SPA navigates to `/runs/<id>`; `JobStatusPip`
   shows `pending`, then `running` within a few seconds.
3. LogViewer streams stdout. LossChart populates as `epoch`-kind
   events arrive over SSE.
4. `[Cancel]` → the `LongJobRunner` SIGTERMs the worker; status
   flips to `cancelled` within ~10 s.
5. Reload the page mid-run. The SSE reconnects via
   `GET /api/jobs/{job_id}/events`; the log resumes and `LossChart`
   re-renders from `progress.jsonl`.
6. After completion the model appears in `/models` with the correct
   sidecar; "Open Eval" launches a prefilled eval against
   `<ml_validation_dir>/clogaelach/recognition/`.

---

## 11. Citations

- `ITrainingRunner` generator methods + `TrainingEvent` shape:
  `pdomain-ocr-training/pdomain_ocr_training/protocols.py:58-247`.
- Raw→public event translation (`epoch`/`metric`/`log`/`done`/`error`):
  `pdomain-ocr-training/pdomain_ocr_training/local.py:78-132, 367-420`.
- `LocalTrainingRunner` in-process thread, no cancellation hook:
  `pdomain-ocr-training/pdomain_ocr_training/local.py:253-364` (docstrings
  `:25-31, 265-270`).
- `DetectionConfig` / `RecognitionConfig` defaults:
  `pdomain-ocr-training/pdomain_ocr_training/protocols.py:85-188`.
- Subprocess submit / supervise / cancel:
  `pdomain-ocr-ops/pdomain_ocr_ops/gpu/local_jobs.py:104-179`.
- Crash-recovery model: `pdomain-ocr-labeler-spa/specs/10-jobs-and-sse.md`.
- Trainer ROADMAP for typeface (a.5) and glyph (g1)/(g2):
  `pdomain-ocr-training/docs/ROADMAP.md`.
