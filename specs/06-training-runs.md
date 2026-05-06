# 06 — Training runs

How the SPA starts, monitors, and finishes a training run. Detection,
recognition, typeface-classification, and glyph-classification share
this surface; per-task differences are §5.

> Required reading: [`01-data-models.md`](01-data-models.md) §3,
> [`02-backend.md`](02-backend.md) §5.4 / §5.5,
> [`04-profiles-and-config.md`](04-profiles-and-config.md) §3,
> [`10-jobs-and-sse.md`](10-jobs-and-sse.md).

---

## 1. Lifecycle

```
[click Start]
   │
   ▼
POST /api/runs ─────────► server: write runs/<id>/{manifest,args}.json
   │                       spawn subprocess via ITrainingRunner.start
   │                       create Job, link Job.run_id = run_id
   ◄── 202 {run_id, job_id}
   │
   ▼
EventSource /api/jobs/{job_id}/events
   │
   │   data: { "type": "log", "stream": "stdout", "line": "..." }
   │   data: { "type": "progress", "current": 3, "total": 100, "message": "epoch 3/100 loss=0.123" }
   │   data: { "type": "metric", "name": "val_cer", "value": 0.045, "step": 3 }
   │   data: { "type": "artefact", "path": "...", "kind": "weights" }
   │   data: { "type": "complete", "exit_code": 0 } | { "type": "failed", "code": "...", ...}
   ▼
SSE close
   │
   ▼
queryClient.invalidate(["run", run_id])
```

A single run is owned end-to-end by one `Job`. Reloading the SPA
mid-run reattaches by hitting `GET /api/jobs/{job_id}/events` again
— the server replays buffered events from a per-job ring (last 1000
events) before resuming live stream.

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
    device: str | None = None             # "auto" (default) | "cuda:0" | "cpu" | "mps"
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
- `args` must validate against the task's pydantic schema (rejects
  unknown keys; `422` with field-level errors).
- `sources` must all exist; for `local` source, the
  `ml-training/<profile>/<task>/` dir must contain at least one
  labelled item. (`409 run.no_training_data`).
- Concurrent runs: at most one running `train` job per
  `(profile, task)` (`409 run.concurrent`). The user can queue
  multiple by submitting them; they enter `pending` and the runner
  picks them up FIFO. ([Q12](../OPEN_QUESTIONS.md): cap queue length?
  enforce one-at-a-time across profiles to avoid VRAM thrash?)

Side effects:

- `runs/<id>/` directory created.
- `manifest.json`, `args.json` written.
- `Run.status = "pending"`, then transitions to `running` once the
  subprocess is up.
- Notification toast: "Training started — 'pd-ga-clogaelach-recognition-...'"
  with link to `/runs/{run_id}`.

---

## 3. Subprocess invocation (local_subprocess runner)

The `local_subprocess` impl of `ITrainingRunner.start`:

```
python -m pd_ocr_trainer.train_<task> --args-from runs/<id>/args.json
```

(Or if we extract `pd-ocr-trainer-core`,
`python -m pd_ocr_trainer_core.train_<task>`. See
[Q3](../OPEN_QUESTIONS.md).)

- Working dir: project root (so doctr's relative imports work).
- Environment: inherited + `HF_HOME=<settings.hf_cache_dir>` if
  set, `CUDA_VISIBLE_DEVICES` filtered to the chosen device, and
  `PD_OCR_TRAINER_PROFILE=<profile>` for parser hooks.
- stdout / stderr: `subprocess.PIPE`, line-buffered, two reader
  threads that emit `JobEvent.log(stream, line)` per line.
- `progress.jsonl` is the **server's** rolled summary — see §4.
- The subprocess writes its own model artefacts to
  `<shared-models>/<profile>/<task>/<model_name>/...` exactly the
  way the legacy trainer does today.

Cancellation:

1. Cancel mark sets `cancellation.requested = True`.
2. Reader threads notice and SIGTERM the process (`process.terminate()`).
3. After 10 s grace, `process.kill()` (SIGKILL).
4. Reader threads drain stdout/stderr to log files, then close.
5. Job state → `cancelled`; Run status → `cancelled`.

Crash recovery:

- If the FastAPI process dies mid-run, on next boot the Run is in
  `running` state but no Job exists. The hydration step
  (`AppState.hydrate_from_disk`) marks such runs as `failed` with
  `exit_code = -1` and appends a `stderr.log` line:
  `"[trainer-spa] process gone before exit; marked failed at boot"`.

---

## 4. Progress + metric extraction

The legacy training scripts emit lines like:

```
Epoch 3/100   loss: 0.123   val_loss: 0.456   val_cer: 0.045
```

`adapters/training/parsers.py` defines a regex per task:

```python
DETECTION_PROGRESS = re.compile(r"^Epoch\s+(?P<current>\d+)/(?P<total>\d+)")
DETECTION_METRICS = re.compile(r"val_(?P<name>\w+):\s*(?P<value>[\d.eE+-]+)")
```

Per stdout line:

1. Try the progress regex. On match, emit `JobEvent.progress(...)`.
2. Try every metric regex on the line. Emit a `JobEvent.metric(name,
   value, step=current_epoch)` for each match.
3. Always emit `JobEvent.log("stdout", line)` regardless.

Server appends the *progress* and *metric* events (not the log
lines) to `runs/<id>/progress.jsonl` for replay and chart rendering.

The frontend `LossChart` reads `progress.jsonl` via
`GET /api/runs/{run_id}/progress` (returns the JSONL as
`application/x-ndjson`) when rendering an old run. While a run is
live, it consumes events directly from the SSE stream.

`progress.jsonl` shape per line:

```json
{"t": 1715035200.123, "type": "progress", "current": 3, "total": 100, "message": "..."}
{"t": 1715035200.456, "type": "metric", "name": "val_cer", "value": 0.045, "step": 3}
```

Cap: 50k events per run on disk; older are GC'd by oldest-first
trim once the file hits the cap. ([Q13](../OPEN_QUESTIONS.md))

---

## 5. Per-task differences

### 5.1 Detection

- Args schema per [`04-profiles-and-config.md`](04-profiles-and-config.md) §3.2.
- Required dataset: `ml-training/<profile>/detection/labels.json`.
- Artefact: `<model_name>.pt` (or `.safetensors`) + sidecar.

### 5.2 Recognition

- Args schema includes `vocab_library` + `custom_characters` →
  resolved via `build_custom_vocab_arg(...)` to the final
  `CUSTOM:<chars>` string before subprocess invocation.
- The "scan training set for missing chars" button on the run form
  hits `POST /api/profiles/{p}/scan-missing-chars` (see
  [`04-profiles-and-config.md`](04-profiles-and-config.md) §2.3) and
  inlines the response into the form's `custom_characters` field.

### 5.3 Typeface classification (M (a.5))

- Reads `ml-training/<profile>/typeface/metadata.jsonl`.
- Architecture TBD ([Q9](../OPEN_QUESTIONS.md)).
- Metric regexes parse `accuracy`, `f1_macro`, per-class accuracy.

### 5.4 Glyph classification (g2)

- Reads `ml-training/<profile>/glyph/metadata.jsonl`.
- Multi-head sigmoid; one head per feature in `feature_heads`.
- Per-feature precision and recall surface as separate metrics.
- Eval gate: per-feature precision ≥ 0.99 for "auto-fill" threshold,
  recall ≥ 0.9 for "suggest" — mirrors `pd-ocr-trainer/docs/ROADMAP.md` (g2).

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
- Legacy form (`pd-{profile}-{task}-...`) is accepted **only as an
  override** the user types in `model_name` explicitly.

The frontend `lib/modelName.ts` parses + renders both shapes for
display.

---

## 7. Run-detail page

Route: `/runs/{run_id}`.

Layout:

```
┌─────────────────────────────────────────────────────────────────┐
│ <breadcrumb> · Profile · Task · model_name · status badge       │
├──────────────────────────────────────────────┬──────────────────┤
│ LossChart (recharts; train/val curves)       │  Sidebar         │
│                                              │  - Args summary  │
│                                              │  - Progress %    │
│                                              │  - ETA           │
│                                              │  - Sources       │
│                                              │  - Artefacts     │
├──────────────────────────────────────────────┴──────────────────┤
│ LogViewer  [stdout|stderr toggle] [auto-scroll] [wrap] [copy]   │
│  ▼ thousands of lines, virtualized                              │
└─────────────────────────────────────────────────────────────────┘
```

Actions:

- `[Cancel]` (only when `status == running`).
- `[Resume from checkpoint]` — disabled for v1; placeholder.
- `[Open Model]` (only when `status == succeeded` and an artefact
  is registered).
- `[Open Eval]` — opens prefilled eval form against this model.
- `[Delete run]` (only when `status` terminal; refuses if
  artefacts exist on disk).

---

## 8. Run-list page

Route: `/runs`.

- Table: started_at | profile | task | kind | status | duration | model_name (link).
- Filters: profile (multi), task (multi), status (multi), kind (multi).
- Paginated (server-side); infinite-scroll.
- Status badge maps to a colour: pending=grey, running=blue,
  succeeded=green, failed=red, cancelled=amber.
- Click row → `/runs/{run_id}`.

---

## 9. Failure surfacing

Common failure modes (mapped to error codes in
[`02-backend.md`](02-backend.md) §6 / [`11-notifications.md`](11-notifications.md)):

| Error code | Trigger | UI surface |
|---|---|---|
| `training.cuda_oom` | OOM keyword in stderr | Toast + sidebar warning + "Reduce batch size" link to clone+edit run. |
| `training.no_training_data` | Empty dataset detected | Form-level error before submit; never reaches the runner. |
| `training.cuda_unavailable` | Pre-flight `_detect_cuda_device()` returned None | Form warning if `device` is `auto`; outright error if user pinned cuda. |
| `training.import_error` | Subprocess failed before printing first line | Run goes `failed`; sidebar shows the captured stderr verbatim. |
| `training.parser_drift` | Progress regex never matches over 30 s of stdout | Soft warning toast; metrics chart stays empty but log streams normally. ([Q14](../OPEN_QUESTIONS.md)) |

---

## 10. Acceptance behaviour

1. Configure recognition defaults for `clogaelach` profile. Click
   "New run". Form prefills from defaults. Override epochs to 5 for
   a smoke test. Click Start.
2. Within 1 s the SPA navigates to `/runs/<id>`. Status badge:
   `pending`. Within 5 s: `running`.
3. LogViewer streams stdout. LossChart populates as
   `Epoch X/Y` lines arrive.
4. `[Cancel]` button → status flips to `cancelled` within ~10 s;
   subprocess exits with SIGTERM-then-SIGKILL.
5. Reload the page mid-run. The SSE reconnects, log resumes
   streaming with no gap; LossChart re-renders the buffered series.
6. After completion, the model appears in `/models` with the
   correct sidecar; "Open Eval" launches a prefilled eval against
   `ml-validation/clogaelach/recognition/`.

---

## 11. Citations

- DetectionTrainingConfig defaults: `pd-ocr-trainer/src/pd_ocr_trainer/ui.py:267-288`.
- RecognitionTrainingConfig defaults: `ui.py:291-318`.
- Subprocess + threaded log capture pattern: `ui.py` training-launch
  callbacks (search for `subprocess.Popen`).
- Trainer ROADMAP for typeface (a.5) and glyph (g1)/(g2):
  `pd-ocr-trainer/docs/ROADMAP.md`.
- Crash recovery model: `pd-ocr-labeler-spa/specs/10-jobs-and-sse.md`.
