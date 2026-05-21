# 17 — Decisions log

Architectural decisions baked into the rest of the specs. Each entry
records what was chosen, what was rejected, and why. New deviations from
any of these require a new entry, not a silent edit to a per-area spec.

> Format borrowed from `pd-ocr-labeler-spa/specs/17-decisions.md`.
> IDs prefixed `D-T<n>` to keep them disjoint from labeler-spa `D-<n>`.
>
> **Re-spec note.** D-T1, D-T3, D-T9, D-T10 were revised — and D-T19–D-T22
> added — when the SPA was re-spec'd onto the `pd-ui` + `pd-ocr-ops` +
> `pd-ocr-training` stack (cross-cut retirement design, 2026-05-21). The
> original D-T1 (training as raw subprocess calls into `pd-ocr-trainer`)
> and the rejected shadcn/ui+Tailwind frontend choice are superseded.

---

## D-T1. Training runs in a worker subprocess driving `ITrainingRunner`

**Decided.** A training run executes in a **worker subprocess**. The
FastAPI backend never imports `torch`/DocTR: it imports only
`pd-ocr-training`'s `ITrainingRunner` Protocol and the `torch`-free typed
config models (`DetectionConfig` / `RecognitionConfig`). The subprocess
builds the config and drives `pd_ocr_training.LocalTrainingRunner`, whose
`TrainingEvent`s are forwarded to the parent as job events. The
subprocess lifecycle is owned by the `pd-ocr-ops` `LongJobRunner`
(D-T20).

**Why.** Three reasons, in priority order:

1. **CUDA isolation.** A failed run must not take down the FastAPI
   process. A subprocess can be killed cleanly; an in-process `torch`
   crash corrupts the parent.
2. **Reliable cancellation.** SIGTERM + grace + SIGKILL on a subprocess
   is reliable. `LocalTrainingRunner` runs training in an in-process
   daemon thread with **no pre-emption mechanism** — abandoning its
   iterator leaves the thread (and the GPU) held until training finishes
   naturally. Running it inside a subprocess restores hard cancellation.
3. **`torch`-free backend.** Keeping the concrete runner in the
   subprocess means the long-lived FastAPI process never loads `torch`.

**Rejected.** Injecting `LocalTrainingRunner` into the FastAPI process
directly. Simpler wiring, but gives up CUDA isolation and hard
cancellation and loads `torch` into the web process — all three of the
reasons above.

**Rejected (original D-T1).** Raw `python -m pd_ocr_trainer.train_<task>`
subprocess calls into the legacy repo. The legacy repo is being retired;
training code now lives behind `ITrainingRunner` in `pd-ocr-training`.

---

## D-T2. Dataset sources — `local` in core, `huggingface` deferred

**Status.** ⏸ **Deferred — post-core-parity.**

**Decided.** Core parity ships the `local` `IDatasetSource` only. The
`huggingface` impl and the multi-source mixing layer are a deferred
post-core-parity milestone (retirement plan Task 13).

**Why.** HF is the legacy trainer's planned cross-machine substrate but
is not part of the working NiceGUI feature set the SPA must reach parity
with first.

---

## D-T3. Runs persisted; jobs are not persisted across restarts

**Decided.** Runs are persisted on disk (`runs/<run_id>/`:
`manifest.json`, `args.json`, `stdout`/`stderr`/`progress.jsonl`). The
job registry itself (D-T20)
is not relied on across a FastAPI restart: an in-progress run found at
boot is reconciled to `failed` with a synthetic "process gone" line.

**Why.** The training subprocess does not survive a backend restart, so
marking running-at-boot runs as `failed` is honest. The on-disk run
directory preserves everything the user needs.

---

## D-T4. dnd-kit for the SPA-local kanban; promotion-ready

**Decided.** The dataset kanban is an **SPA-local** component (a `pd-ui`
gap) built with `@dnd-kit/core` + `@dnd-kit/sortable` +
`@dnd-kit/utilities`. KeyboardSensor for a11y; PointerSensor for mouse.
It is built as a *promotion-ready* component — styled with `pd-ui`
design tokens, exposing a clean self-contained interface — so lifting it
into `pd-ui` later is cheap.

**Why.** HTML5 native DnD has a11y dead-ends (no keyboard support) and
styling pain; dnd-kit is the modern React default. Building SPA-local
first avoids pre-generalizing a component no other app needs yet (YAGNI);
building it promotion-ready keeps the door open.

**Rejected.** `react-dnd` (heavier, less maintained). Native HTML5 (a11y
dead-end). Pre-promoting to `pd-ui` now (YAGNI — no second consumer).

---

## D-T5. profile.toml is the source of truth for language + typeface

**Decided.** Per-profile `profile.toml` in `ml-training/<profile>/`,
mirrored in `ml-validation/<profile>/`. Schema in
[`04-profiles-and-config.md`](04-profiles-and-config.md) §4.

**Mirror policy.** Both files must agree; disagreement is a 409 at load
time, resolved via the SPA dialog or by manual edit.

**Why.** Language + typeface belong next to the data, not in an
out-of-band registry. TOML is human-editable.

---

## D-T6. New model-name convention; legacy is read-only

**Decided.** New training runs mint `pd-<lang>-<typeface>-<task>-<date>`.
Legacy `pd-<profile>-<task>-<...>` names are displayed and evaluated but
never minted.

**Why.** Aligns with the trainer ROADMAP and `pd-ocr-cli`'s expected
name form; gives a coexistence window without a breaking-change moment.

---

## D-T7. PD_OCR_TRAINER_SPA_* env-var prefix

**Decided.** All env vars use the `PD_OCR_TRAINER_SPA_` prefix (not the
legacy `PD_OCR_TRAINER_`).

**Why.** Side-by-side coexistence with the legacy trainer until it is
retired. Different prefixes let users set both without footguns. `make
doctor` prints the resolved values.

---

## D-T8. Port 8081 default

**Decided.** Default backend port 8081 (labeler-spa uses 8080). Frontend
dev port 5174.

**Why.** Coexistence — same reason as D-T7.

---

## D-T9. doctr is a dependency of `pd-ocr-training`

**Status.** ✅ **Superseded** by the retirement design.

**Decided.** DocTR is a normal dependency of `pd-ocr-training`, declared
in that package's `pyproject.toml`. The SPA does not vendor doctr, does
not clone it, and is not involved in any `CUSTOM:` vocab patching — that
is entirely a `pd-ocr-training` concern.

**Why.** The original decision (users clone `mindee/doctr` next to the
legacy checkout) was a legacy-trainer workflow. With training code
extracted into `pd-ocr-training`, doctr is just one more dependency of
that package.

---

## D-T10. SSE progress contract is owned by `pd-ocr-ops`

**Decided.** The job event stream — event kinds, replay/reconnect
behaviour, and the SSE endpoint shape — is whatever the `pd-ocr-ops`
`LongJobRunner` provides. The SPA does not hand-roll a per-job event
ring; it consumes the `LongJobRunner` contract.

**Why.** `LongJobRunner` already owns job lifecycle and progress
streaming (D-T20). Re-implementing a parallel buffer in the SPA would
duplicate that and risk divergence. Reconnect-after-restart falls back
to on-disk `progress.jsonl` per D-T3.

---

## D-T11. Per-row dataset licensing

**Status.** ⏸ **Deferred — post-core-parity.**

**Decided.** Per-row SPDX `license` on dataset rows, required at HF
publish time, is part of the deferred HF-datasets milestone (Task 13),
not core parity.

**Why.** Licensing matters only at the HF publish boundary, which is
itself deferred (D-T2).

---

## D-T12. Driver contract from M0; no peer driver repo in v1

**Decided.** `data-testid` and URL invariants are part of the contract
from M0 (per [`13-driver-contract.md`](13-driver-contract.md)). A peer
`pd-ocr-trainer-spa-driver` repo is **not** built in v1; the contract
exists so one *can* be built later.

**Why.** The trainer has no comparable mechanical pre-pass need —
starting / monitoring training is what the human is there for. Keep the
seam open without spending the build-it cost.

---

## D-T13. No global "current run" state on the backend

**Decided.** The backend does not track "the user's currently-selected
run." Every request is stateless w.r.t. user UI focus; that lives on the
frontend.

**Why.** Mirrors labeler-spa D-023. Multi-tab is then trivial.

---

## D-T14. recharts for charts

**Decided.** `recharts` for LossChart + EvalMetricsTable visualizations.

**Why.** Charts here are simple line + bar — not a custom canvas
overlay. recharts has good React 19 compatibility and a small footprint.

**Rejected.** D3-direct (more code per chart); echarts (heavier).

---

## D-T15. Single-runner training-job concurrency in v1

**Decided.** One `train` job runs at a time across the entire backend.
Submitting another while one runs queues it. This is enforced through
the `pd-ocr-ops` `LongJobRunner`.

**Why.** Training is GPU-bound; running two on one GPU thrashes VRAM.
One-at-a-time with explicit opt-in for parallel is the cleaner default.

**Rejected.** Per-(profile, task) queues — doesn't solve VRAM contention.

---

## D-T16. Sidecar schema is append-only by convention

**Decided.** The model sidecar (`<model_name>.metadata.json`) gains new
fields as optional-with-defaults. No explicit schema version.

**Why.** Optional fields are forward+backward compatible; an explicit
version forces lockstep upgrades for no real win in this read-mostly
shape.

---

## D-T17. Each spec-writing iteration ships one or two specs

**Decided.** During the spec-writing phase, commits land per spec-pair.
No branchy refactors mid-spec.

**Why.** Reviewability + clean rollback.

(Applies only during spec authorship; once milestone implementation
starts, normal commit hygiene applies.)

---

## D-T18. Workspace .gitignore tracks the new repo

**Decided.** `pd-ocr-trainer-spa/` is in the workspace `.gitignore`
alongside the other `pd-*` repos so the workspace's own git stays clean.

**Why.** Mirrors labeler-spa precedent.

---

## D-T19. Frontend built on the `pd-ui` component library

**Decided.** The SPA frontend is built on **`pd-ui`**
(`@concavetrillion/pd-ui`, consumed from the `pd-index-npm` registry):
`AppShell`, `TopNav`, `Card`, `Accordion`, `Field`/`FieldRow`, `Button`,
`Select`, `Progress`, `JobStatusPip`, the `useLongJob` hook, and the
`tokens.css` / `primitives.css` design tokens. No direct Tailwind, no
shadcn/ui.

**Why.** `pd-ui` is the workspace-standard shared frontend library; the
shipped `pd-ocr-labeler-spa` and `pd-ocr-simple-gui` are built on it.
Reusing it gives visual + behavioural consistency across the suite and
removes per-app component maintenance.

**Rejected (original choice).** shadcn/ui + Tailwind 3.4. Predated the
workspace `pd-ui` standardization decision; would fork the suite's UI.

**SPA-local exceptions.** Two components have no `pd-ui` counterpart —
the DnD kanban (D-T4)
and the streaming-log viewer. Both are built SPA-local but
*promotion-ready* (pd-ui tokens, clean interfaces); promoting them into
`pd-ui` is a deferred follow-up, not pre-done (YAGNI).

---

## D-T20. Long jobs via the `pd-ocr-ops` `LongJobRunner`

**Decided.** Long-running jobs (training runs, and any future long
operation) are managed by the `pd-ocr-ops` `LongJobRunner`: a job
registry, per-job status, and an SSE event stream. The SPA does not
hand-roll a `core/job_runner.py`.

**Why.** `pd-ocr-ops` is the workspace-standard ops library; its
`LongJobRunner` is the canonical long-job seam every `pd-*` SPA backend
uses. Reusing it removes duplicated job-lifecycle code and a class of
restart/SSE bugs.

**Rejected.** A SPA-local in-memory job runner (the original D-T3
mechanism). Duplicates `pd-ocr-ops` for one consumer.

---

## D-T21. Suite plumbing via `pd-ocr-ops` `mount_routes`

**Decided.** The FastAPI app mounts `pd-ocr-ops` suite routes via
`pd_ocr_ops.suite.mount_routes(app, adapters)` — registry, UI-prefs,
sibling-spawn, and the central `/healthz` endpoint. The SPA does not
hand-roll these.

**Why.** Workspace-standard suite integration; matches the shipped
`pd-ocr-labeler-spa` and `pd-ocr-simple-gui` backends.

---

## D-T22. The training job/run is surfaced in the UI

**Decided.** A training run is observable in the SPA, not
fire-and-forget. The UI shows: a `JobStatusPip` for run state, live
progress (`Progress` driven by `useLongJob` SSE), a streaming log panel,
and run history. Cancellation (D-T1) is a UI action.

**Why.** Starting and monitoring training *is* the user's job
(D-T12); the run must be fully visible. With the training worker isolated in a
subprocess, the UI surfacing is the only way the user sees what the
subprocess is doing.

---

## D-T23. Kanban reassignment is staged client-side, then applied

**Decided.** Dataset-kanban drags rearrange pages in **client-side
staging state only** — no request per drag. An explicit "Apply" commits
the whole reassignment through one batch endpoint
(`POST /api/profiles/{profile}/datasets/apply` with the full target
split assignment); a "Discard" resets staging to server state. Other
user actions (config submit, run start/cancel) remain per-action.

**Why.** Split reassignment moves files on disk (`ml-training/` ↔
`ml-validation/`). Per-drag commits cause disk churn and transient
half-applied states. Staging lets the user arrange freely, review a
pending diff, and commit atomically — or back out.

**Trade-off.** Staged moves are per-tab client state, so two tabs can
diverge until Apply. Consistent with D-T13 (UI focus lives on the
frontend); acceptable.

**Rejected.** Per-drag autosave (the original dataflow). This also
deviates deliberately from labeler-spa's server-side-autosave rule —
justified because the labeler edits per-word state cheaply while the
trainer kanban moves files in bulk.
