# 17 — Decisions log

Architectural decisions baked into the rest of the specs. Each
entry records what was chosen, what was rejected, and why. New
deviations from any of these require a new entry, not a silent
edit to a per-area spec.

> Format borrowed from `pd-ocr-labeler-spa/specs/17-decisions.md`.
> IDs prefixed `D-T<n>` to keep them disjoint from labeler-spa
> `D-<n>` ids.

---

## D-T1. Training runs as subprocesses, not in-process imports

**Decided.** `ITrainingRunner.local_subprocess` spawns
`python -m pd_ocr_trainer.train_<task>` and reads stdout/stderr
line-by-line.

**Why.** Three reasons, in priority order:

1. **CUDA isolation.** A failed run shouldn't take down the FastAPI
   process. Subprocesses get killed cleanly; in-process torch
   crashes corrupt the parent.
2. **Stdout streaming.** The legacy training scripts print progress
   in human-readable form. Capturing them as a stream is trivial;
   re-plumbing them as in-process callbacks would mean rewriting
   the trainer code.
3. **Cancellation.** SIGTERM + grace + SIGKILL on a subprocess is
   reliable; cancelling an in-process torch loop is not.

**Rejected.** In-process import + thread-based progress callbacks.
Tighter coupling to `pd-ocr-trainer` and worse failure modes for
no real win.

---

## D-T2. Two dataset-source impls, three eventually

**Decided.** `IDatasetSource` ships with `local` and `huggingface`
in v1. Future `s3` / `gcs` / `azure` impls can land later. The
mixing layer (multiple sources per run) is part of v1.

**Why.** The trainer ROADMAP commits to HF as the cross-machine
substrate. S3/GCS would be a third option for users who don't
want to publish data to HF; not strictly needed for v1.

---

## D-T3. JobRunner is in-memory, runs survive across restarts

**Decided.** Jobs are not persisted across FastAPI restarts. Runs
*are* (manifest.json, args.json, stdout/stderr/progress.jsonl).
On reload, in-progress runs become `failed` with a synthetic
"process gone" stderr line.

**Why.** Persisting the live event ring + queue across restarts is
complex and the marginal value is small (the user can just look at
on-disk logs). Marking running-at-boot as failed is honest — the
subprocess is gone too.

**Rejected.** Persisting jobs to a SQLite-on-disk queue. Adds DB
infra for one consumer.

---

## D-T4. dnd-kit, not native HTML5 drag

**Decided.** Kanban uses `@dnd-kit/core` + `@dnd-kit/sortable` +
`@dnd-kit/utilities`. KeyboardSensor for a11y; PointerSensor for
mouse.

**Why.** The legacy NiceGUI kanban uses raw HTML5 drag events
(`draggable=true`, `dragstart`, `dragover.prevent`, `drop`). HTML5
DnD has known a11y issues (no keyboard support) and styling pain
(can't change cursor or ghost). dnd-kit is the modern React
default; sized appropriately for a list-based kanban.

**Rejected.** `react-dnd` (heavier API, less actively maintained
than dnd-kit). Native HTML5 (a11y dead-end).

---

## D-T5. profile.toml is the source of truth for language + typeface

**Decided.** Per-profile `profile.toml` in
`ml-training/<profile>/` and mirrored in `ml-validation/<profile>/`.
Schema in [`04-profiles-and-config.md`](04-profiles-and-config.md) §4.

**Why.** Language + typeface are the two new attributes from the
trainer ROADMAP and need to live next to the data, not in some
out-of-band registry. TOML chosen over JSON because it's
human-editable.

**Mirror policy.** Both files must agree; disagreement is a 409 at
load time. The user resolves via the SPA dialog or by editing one
of the files manually.

---

## D-T6. New model-name convention; legacy is read-only

**Decided.** New training runs mint `pd-<lang>-<typeface>-<task>-<date>`.
Legacy `pd-<profile>-<task>-<...>` names are displayed and
evaluated but never minted. Publish refuses legacy-form names.

**Why.** Aligns with trainer ROADMAP §Cross-repo dependencies,
where pd-ocr-cli expects the new form. We don't want a
breaking-change moment; we want a window where both forms coexist
and only the new form is published.

---

## D-T7. PD_OCR_TRAINER_SPA_* env-var prefix

**Decided.** All env vars use the `PD_OCR_TRAINER_SPA_` prefix
(not the legacy `PD_OCR_TRAINER_`).

**Why.** Side-by-side coexistence with the legacy trainer must work.
Different env-var prefixes let users set both — different roots,
different shared-models dirs — without footguns.

**Trade-off.** Users have to learn a second prefix. Mitigation:
`make doctor` prints the resolved values for both prefixes.

---

## D-T8. Port 8081 default

**Decided.** Default port is 8081 (labeler-spa uses 8080; pgdp-prep
uses something else). Frontend dev port is 5174 (vite dev) instead
of 5173 (pgdp-prep) — both can run side-by-side.

**Why.** Same reason as D-T7: coexistence.

---

## D-T9. doctr clone stays external in v1

**Decided.** Users continue to clone `mindee/doctr` next to their
pd-ocr-trainer checkout and apply the `CUSTOM:` vocab patch (per
`pd-ocr-trainer/README.md`). The SPA doesn't vendor doctr.

**Why.** Vendoring would force the legacy trainer to also use the
vendored copy or to coexist with two doctr clones. Both options
are worse than keeping the existing convention.

**Future.** Once the legacy trainer is retired (post M9 / cutover),
revisit vendoring.

---

## D-T10. SSE replay buffer is per-job, in memory, last 1000

**Decided.** Each `Job` has a 1000-event ring in memory plus
on-disk `progress.jsonl` (events of type progress/metric/artefact).
Reconnect within the FastAPI lifetime resumes from the ring; after
restart, the SPA falls back to polling + on-disk progress.

**Why.** Easy to implement, covers the 99% case (tab reconnect
within 5 minutes). Persisting the ring would marginally improve
the post-restart case but require a write per event (or every N
events with a flush).

---

## D-T11. License is per-row + required at publish time

**Decided.** Every dataset row carries a per-row `license` (SPDX
identifier). Publish refuses with `publish.license_missing` when
any row lacks it.

**Why.** Per
`pd-ocr-trainer/docs/ROADMAP.md` §License. Datasets often mix
sources; per-row licensing is the only honest representation.

---

## D-T12. Driver contract from M0; no peer driver repo in v1

**Decided.** `data-testid` and URL invariants are part of the
contract from M0 (per [`13-driver-contract.md`](13-driver-contract.md)).
A peer `pd-ocr-trainer-spa-driver` repo is **not** built in v1; the
contract exists so one *can* be built later.

**Why.** The labeler driver ships value because pre-passes save
human labelling time. The trainer doesn't have a comparable
mechanical pre-pass need: starting / monitoring training is what
the human's there for. We keep the seam open without spending the
build-it cost.

---

## D-T13. No global "current run" state on the backend

**Decided.** Backend doesn't track "the user's currently-selected
run." Every request is stateless w.r.t. user UI focus; that lives
on the frontend.

**Why.** Mirrors labeler-spa D-023. Multi-tab is then trivial.

---

## D-T14. recharts for charts; Konva not needed

**Decided.** `recharts` for LossChart + EvalMetricsTable
visualizations.

**Why.** Charts here are simple line + bar; not a custom canvas
overlay like the labeler-spa's image viewport. recharts has good
React 19 compatibility and a small footprint.

**Rejected.** D3-direct (more code per chart), echarts (heavier,
less idiomatic with React).

---

## D-T15. Single-runner training-job concurrency in v1

**Decided.** One `train` job runs at a time across the entire
backend. Submitting another while one runs queues it.

**Why.** Training is GPU-bound; running two simultaneously on a
single GPU thrashes VRAM. Even on a multi-GPU box, the cleaner
default is one-at-a-time and explicit user opt-in for parallel.
v2 can introduce per-device queues.

**Rejected.** Per-(profile, task) queues. Doesn't solve the VRAM
contention problem; one user with two profiles still thrashes.

---

## D-T16. Sidecar schema is append-only by convention

**Decided.** Model sidecar (`<model_name>.metadata.json`) gains
new fields as optional with defaults. No explicit schema version.

**Why.** Same as labeler-spa's UserPageEnvelope policy: optional
fields are forward+backward compatible; an explicit version field
forces lockstep upgrades for no real win in this read-mostly
shape. ([Q6](../OPEN_QUESTIONS.md) keeps the option open if
something forces it.)

---

## D-T17. Each /loop iteration ships one or two specs, one commit each

**Decided.** During the spec-writing phase, commits land per
spec-pair. No branchy refactors mid-spec.

**Why.** Reviewability + clean rollback. Set by the
[overnight loops feedback memory](../../README.md) — small commits
preferred.

(This decision applies only during M-pre-0 / spec authorship; once
M0 starts, normal commit hygiene applies.)

---

## D-T18. Workspace .gitignore tracks the new repo

**Decided.** `pd-ocr-trainer-spa/` is added to the workspace
`.gitignore` alongside the other `pd-*` repos so the workspace's
own git stays clean.

**Why.** Mirrors labeler-spa precedent.
