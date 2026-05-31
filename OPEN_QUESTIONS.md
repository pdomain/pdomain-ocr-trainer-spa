# Open Questions for `pdomain-ocr-trainer-spa`

Questions the spec authors could not resolve from the source
material alone. Each entry: **Q** (the question), **Context**
(why it matters), **Options** (with trade-offs), **Recommendation**
(spec author's bet), **Blocks** (which milestones can't start
until resolved). Once you answer, a **Resolution** line links the
ADR added to [`specs/17-decisions.md`](specs/17-decisions.md).

> Specs cite these as `([Qn](OPEN_QUESTIONS.md))`. Specs treat them
> as unresolved until you've recorded an answer here.

---

## Critical (block M0–M3)

### Q3. Source of training entry points: import or extract?

> **✅ Superseded — resolved by the retirement re-spec (2026-05-21).**
> Training code is neither imported from the legacy `pdomain-ocr-training`
> nor extracted into a `-core` package: it now lives in the
> `pdomain-ocr-training` library behind the `ITrainingRunner` Protocol
> (D-T1). The SPA worker imports `pdomain_ocr_training.LocalTrainingRunner`;
> the web process imports only the `torch`-free config models. None
> of options (A)/(B)/(C) below apply. **Resolution:** D-T1.

**Context.** The SPA invokes
`python -m pdomain_ocr_training.train_<task>` from a subprocess
(D-T1). Two ways to get those scripts:

**Options.**

- **(A) Import from existing `pdomain-ocr-training`.** Add it as a Python
  dependency via uv. The SPA's wheel installs it transitively; the
  `pdomain-ocr-trainer-ui` script can find `pdomain_ocr_training.train_*` on
  the PYTHONPATH.
- **(B) Extract a slim `pdomain-ocr-training-core` package** that holds
  only `dataset_store.py`, `train_detect.py`, `train_recog.py`,
  `train_typeface.py` (when it lands), `train_glyph.py`,
  `utils.py`. The legacy `pdomain-ocr-training` (UI) and the new
  `pdomain-ocr-trainer-spa` both depend on it. `pdomain-ocr-training-core`
  ships with no UI dependencies.
- **(C) Vendor copies inside `pdomain-ocr-trainer-spa`.** Worst — fork.

**Recommendation.** **(B)** if we're committing to retire the
legacy UI eventually. **(A)** if we want to ship the SPA without
touching the legacy trainer at all. Initial preference: **(A)** for
the M0–M5 stretch, refactor to **(B)** as part of M6 if the
import surface ends up tangled with NiceGUI imports.

**Blocks.** M6 (training runs); a final answer is needed before
the SPA ships its first real run, but M0–M5 can proceed under
either choice.

---

### Q5. profile.toml mirror conflict resolution

**Context.** D-T5 puts `profile.toml` in both
`ml-training/<name>/` and `ml-validation/<name>/`. They must
agree. If they don't (e.g. user manually edited only one):

**Options.**

- **(A)** 409 at load with a "resolve" link in the SPA that lets the
  user pick a winner.
- **(B)** Last-modified wins; silently mirror.
- **(C)** Prefer the training side; silently overwrite the
  validation side.

**Recommendation.** **(A)** — silent overwrites are footguns.

**Blocks.** M3 profile lifecycle. Default to **(A)** unless you
say otherwise.

---

### Q7. Env-var prefix `PD_OCR_TRAINER_SPA_*`?

**Context.** D-T7 picks this prefix to coexist with the legacy
`PD_OCR_TRAINER_*`. But it's verbose.

**Options.**

- **(A) `PD_OCR_TRAINER_SPA_*`** — explicit, no overlap.
- **(B) `PD_TRAINER_*`** — shorter; risks collision if pdomain-ocr-cli
  ever invents a related prefix.
- **(C) `PD_OCR_TRAINER_*`** with a runtime check that warns when
  legacy values are detected.

**Recommendation.** **(A)** for clarity. Verbose is fine for env
vars users set once and forget.

**Blocks.** M1 (Settings).

---

### Q26. doctr clone — same external as legacy or vendored?

> **✅ Superseded — resolved by the retirement re-spec (2026-05-21).**
> DocTR is a normal dependency of `pdomain-ocr-training`, declared in that
> package's `pyproject.toml`. The SPA neither clones nor vendors
> doctr, and any `CUSTOM:` vocab handling is a `pdomain-ocr-training`
> concern. Options (A)/(B)/(C) no longer apply. **Resolution:** D-T9.

**Context.** Legacy trainer requires the user to clone
`mindee/doctr` and patch `train_pytorch.py`. D-T9 keeps that
convention.

**Options.**

- **(A)** Same external clone as legacy.
- **(B)** Vendor a fork as a git submodule under `pdomain-ocr-trainer-spa/vendor/doctr`.
- **(C)** Upstream the `CUSTOM:` patch into mindee/doctr; eliminate
  the vendoring problem entirely.

**Recommendation.** **(A)** through M9. Pursue **(C)** as a
parallel side-quest; if upstream accepts, retroactively flip to
no-clone-needed.

**Blocks.** M6 (training runs) — but only as a documentation
question; the SPA itself doesn't depend on the choice.

---

## Important (block M4–M9)

### Q1. dnd-kit is the kanban DnD library?

**Context.** The legacy NiceGUI kanban uses HTML5 DnD; D-T4 picks
dnd-kit for the SPA.

**Options.**

- **(A) `@dnd-kit/core`** — modern, a11y-friendly, idiomatic.
- **(B) `react-dnd`** — older, larger.
- **(C) Native HTML5 DnD via thin wrapper.** A11y dead-end.

**Recommendation.** **(A)** dnd-kit.

**Blocks.** M4 (kanban).

---

### Q2. Charting: recharts?

**Context.** LossChart, EvalMetricsTable bar charts.

**Options.**

- **(A) recharts.** Default React choice; ~100 KB; React 19 compatible.
- **(B) chart.js + react-chartjs-2.** Battle-tested; canvas-based.
- **(C) D3 direct.** More code per chart.

**Recommendation.** **(A)** recharts.

**Blocks.** M6 (training-run loss chart), M7 (eval metrics).

---

### Q11. copy-to-datasets — always async, or sync below threshold?

**Context.** The legacy trainer's `save_assignments` is sync. With
30+ pages it can take seconds. The SPA could:

**Options.**

- **(A)** Always create a `Job` (kind=`copy-to-datasets`); SPA
  monitors via SSE.
- **(B)** Sync below 30 items; async above. Branch in client.
- **(C)** Sync up to 5 s server-side timeout; auto-flip to job + 202
  if it overruns. Most complex.

**Recommendation.** **(A)** for uniformity — every long-ish thing
is a Job.

**Blocks.** M4 (kanban copy-to-datasets).

---

### Q12. Training queue cap; cross-profile concurrency?

**Context.** D-T15 caps train-job concurrency to one. Two
sub-questions:

- **(a)** Should the SPA cap the queue length? Currently unbounded.
- **(b)** Should the cap be per-(profile, task) or global?

**Options for (a).**

- **(A1)** No cap; user can queue indefinitely.
- **(A2)** Cap at 5; reject the 6th with `429`.
- **(A3)** Cap at 1 (the running one + 0 in queue) — fail-fast.

**Options for (b).**

- **(B1)** Global one-at-a-time (current default).
- **(B2)** Per-(profile, task) one-at-a-time; multiple GPUs assumed.

**Recommendation.** **(A1)** + **(B1)** for v1. Revisit when
multi-GPU users complain.

**Blocks.** M6.

---

### Q15. HF read vs publish gated by separate flags?

**Context.** `Settings.enable_hf_publish` gates the publish flow.
HF read (M10) is a separate concern; should it have its own
flag?

**Options.**

- **(A)** Single `enable_hf` flag covers both.
- **(B)** `enable_hf_read` (default true) + `enable_hf_publish`
  (default false; explicit opt-in to avoid accidental uploads).

**Recommendation.** **(B)**. Reads are low-risk, writes need
intentionality.

**Blocks.** M10, M11.

---

### Q24. Build a peer `pdomain-ocr-trainer-spa-driver` repo?

**Context.** D-T12 keeps the door open but doesn't build it.

**Options.**

- **(A)** No; the contract exists so a driver *could* be built later.
- **(B)** Yes, after M9. Mechanical pre-passes for "create profile,
  drag known-good DocTR exports, kick off training, wait, archive
  result" are valuable in CI.

**Recommendation.** **(A)** for v1. Revisit if a clear pre-pass
need emerges.

**Blocks.** Nothing.

---

### Q27. `pdomain-ocr-ops` `LongJobRunner` subprocess-stdout event parser

**Context.** D-T20 puts long-job lifecycle on the `pdomain-ocr-ops`
`LongJobRunner`. `LocalLongJobRunner.submit_with_process` spawns and
supervises the training worker subprocess, but as of 2026-05-21 it
only records the exit code and the last stderr line — it does **not**
parse the subprocess's stdout into `job_events`. `_append_event` is
private; there is no public emit/parse API. So `stream_events()`
yields only terminal state, and the SPA's live progress bar + log
stream would be blank for the whole run.

[`02-backend.md`](specs/02-backend.md) §5.2 proposes the worker emit
one `@@PDEVENT@@ {json}` stdout line per `TrainingEvent`; something
must parse those into `JobEvent`s.

**Options.**

- **(A)** `pdomain-ocr-ops` adds a documented subprocess-stdout →
  `JobEvent` parser keyed on the `@@PDEVENT@@` prefix, wired into
  `_supervise`. The canonical contract lives in `pdomain-ocr-ops`; every
  `pdomain` SPA reusing `submit_with_process` gets progress for free.
- **(B)** `pdomain-ocr-ops` exposes a public `emit_event(job_id, ...)` API
  and the worker calls back over HTTP/IPC. More moving parts; needs a
  reachable endpoint.
- **(C)** The SPA does not use `submit_with_process`; it manages the
  worker subprocess itself, parses stdout, and uses `LongJobRunner`
  only as a status registry. Rejected — contradicts D-T20 ("the SPA
  does not hand-roll a job runner") and forks job-lifecycle code.

**Recommendation.** **(A)** — a stdout-line parser in `pdomain-ocr-ops` is
the smallest change and keeps the job contract in one place. The
`@@PDEVENT@@` line format in `02-backend.md` §5.2 is the proposed
wire contract.

**Tracking.** Filed as `pdomain/pdomain-ocr-ops#76`.

**Blocks.** M6 progress streaming (training runs are submittable
without it, but show no live progress until it lands). Cross-repo:
the work itself is `pdomain-ocr-ops#76`.

---

## Nice-to-have (block M10+ or polish)

### Q4. TypefaceEnum.typeface validation timing

**Context.** The literal value `typeface` is only valid on
classifier datasets/models. Validate at:

**Options.**

- **(A)** Profile create/edit: never accept `typeface` as a
  detection/recognition profile's typeface field.
- **(B)** At publish time only (current spec).

**Recommendation.** **(B)** keeps profile create flexible. Some
profiles temporarily span typefaces during data ingest.

**Blocks.** M3 if **(A)** chosen; otherwise M11.

---

### Q6. Explicit `sidecar_schema: int` field?

**Context.** D-T16 says no. But a future field might force a
behavioural change in older readers.

**Options.**

- **(A)** No version field. Append-only convention.
- **(B)** Add `sidecar_schema: 1` from M7 to keep the option open.

**Recommendation.** **(A)** until proven wrong.

**Blocks.** M7 (sidecar IO).

---

### Q8. HF publish: wrap existing `push_to_hf_hub` or new path?

**Context.** `train_detect.py` and `train_recog.py` already call
`push_to_hf_hub`. The SPA could:

**Options.**

- **(A)** Wrap the existing call in `IModelRegistry.huggingface_hub.publish`.
- **(B)** New path that uploads model artefacts directly via
  `HfApi.upload_folder`.

**Recommendation.** **(B)** for cleaner separation: the trainer
should write artefacts; the registry should publish them. Don't
couple training to publishing.

**Blocks.** M11.

---

### Q9. Typeface classifier architecture

**Context.** ROADMAP (a.5) says "small image-classification model
(architecture TBD)". The SPA needs a default.

**Options.**

- **(A)** `mobilenet_v3_small` — small, fast, decent accuracy.
- **(B)** `efficientnet_b0` — slightly bigger, very strong.
- **(C)** A custom 4-conv stack — easiest to retrain on small data.

**Recommendation.** **(A)** for v1. Calibrate on real data once
M12 lands.

**Blocks.** M12.

---

### Q10. Glyph classifier multi-head shape

**Context.** ROADMAP (g2) says "multi-head sigmoid (one head per
binary feature)".

**Options.**

- **(A)** Shared trunk + N independent sigmoid heads.
- **(B)** One large softmax over `2^N` joint classes (rejected: doesn't scale).
- **(C)** N independent classifiers (rejected: 4× the parameter count).

**Recommendation.** **(A)** — shared trunk, per-feature head.

**Blocks.** M14.

---

### Q13. progress.jsonl 50k cap right value?

**Context.** The cap protects against runaway runs. 50k is ~one
event per training step for a 50-epoch run with 1000 steps each.

**Options.**

- **(A)** 50k.
- **(B)** 100k.
- **(C)** No cap; rotate per-run if it grows beyond 100 MB.

**Recommendation.** **(A)** start; revisit if real runs hit it.

**Blocks.** Nothing critical (M6 ships either way).

---

### Q14. parser_drift soft warning threshold

> **✅ Superseded — resolved by the retirement re-spec (2026-05-21).**
> `pdomain-ocr-training` emits structured `TrainingEvent`s, so the SPA no
> longer regex-parses stdout for progress. The `training.parser_drift`
> failure mode is retired; the residual "no progress" case (a worker
> that never reaches its first `epoch` event) surfaces as
> `training.import_error` / `training.worker_died`. No threshold to
> pick. **Resolution:** [`06-training-runs.md`](specs/06-training-runs.md) §4, §9.

**Context (historical).** When the progress regex failed to match
for 30 s of stdout, fire `training.parser_drift`. 30 s arbitrary.

---

### Q16. Regression-alert webhook spec location

**Context.** [`07-evaluation-and-metrics.md`](specs/07-evaluation-and-metrics.md) §7
mentions a CI webhook for regressions. Spec lives where?

**Options.**

- **(A)** `pdomain-ocr-trainer-spa/scripts/regression_alert.py` + a
  README. Single-script, single-repo.
- **(B)** New `pdomain-ml-ci/` repo for cross-repo CI helpers.

**Recommendation.** **(A)** until a second consumer appears.

**Blocks.** Nothing critical.

---

### Q17. `hf_default_owner` default

**Context.** §2 of [`09-hf-integration.md`](specs/09-hf-integration.md).

**Options.**

- **(A)** Default to `Settings.hf_default_owner` (env var); empty
  if unset.
- **(B)** Default to `whoami()` from the HF token at startup.
- **(C)** Refuse to default — user must enter on every publish.

**Recommendation.** **(B)**. Read once at startup; cache.

**Blocks.** M11.

---

### Q18. Source weight normalization in sidecar

**Context.** When the user passes `[(local, 0.5), (hf, 0.5)]`, do
we record `0.5/0.5` or normalize?

**Options.**

- **(A)** Record user-asked weights verbatim.
- **(B)** Record post-normalization weights (always sum to 1).

**Recommendation.** **(A)** — preserves intent. The
WeightedRandomSampler will normalize internally.

**Blocks.** M10.

---

### Q19. HF LFS quota handling

**Context.** Synth datasets are tens of GB; LFS quotas may bite.

**Options.**

- **(A)** Surface the upstream `LfsQuotaExceededError` as
  `hf.lfs_quota` with a link to HF settings.
- **(B)** Pre-flight a quota-check before upload start.

**Recommendation.** **(A)** for v1. Pre-flighting requires API
calls that may not exist on private repos.

**Blocks.** M11.

---

### Q20. Persist in-memory job event ring across restarts?

**Context.** D-T10 says no.

**Options.**

- **(A)** No. SPA falls back to polling on restart.
- **(B)** Yes, write per-event to `runs/<id>/events.jsonl` with
  fsync every N events.

**Recommendation.** **(A)** until a real user complains.

**Blocks.** Nothing critical.

---

### Q21. Training subprocess detached/daemon at FastAPI restart?

**Context.** When the FastAPI process dies, the training subprocess
is currently a child (dies with parent). If we make it daemon
(survive parent death), we could *attempt* to reattach.

**Options.**

- **(A)** Child of FastAPI. Simple. Subprocess dies with parent.
- **(B)** `setsid()` + reattach via PID file. Survival across
  restarts; reattach is fiddly.
- **(C)** systemd-style supervisor process.

**Recommendation.** **(A)** for v1. Revisit if losing a 4-hour run
to a crash becomes a real complaint.

**Blocks.** Nothing critical.

---

### Q22. Persist banner dismissals per-browser?

**Context.** [`11-notifications.md`](specs/11-notifications.md) §3
keeps dismissals in `sessionStorage`.

**Options.**

- **(A)** sessionStorage (per-tab, lost on close).
- **(B)** localStorage (per-browser, persists).
- **(C)** Server-side per-user (we have no users — would be
  per-token).

**Recommendation.** **(A)** until users complain that they have to
re-dismiss the same banner every session.

**Blocks.** M8.

---

### Q23. Command palette (Ctrl+K)?

**Context.** [`12-hotkeys-a11y.md`](specs/12-hotkeys-a11y.md) §2
flags this for v2.

**Options.**

- **(A)** Don't build in v1.
- **(B)** Build a minimal one in M8 (just navigation: profiles,
  runs, models, eval).

**Recommendation.** **(A)** — first ship the basics; add palette
when navigation friction is real.

**Blocks.** M8 polish.

---

### Q25. MPS slow-arch warning specifics

**Context.** [`15-deployment-dev.md`](specs/15-deployment-dev.md) §8
flags some DocTR archs that fall back to CPU on MPS.

**Options.**

- **(A)** Hard-code a list of "safe on MPS" archs and warn on the rest.
- **(B)** Soft-warn on any MPS device-pin and let the user proceed.
- **(C)** Refuse to run unless user passes `--allow-mps-cpu-fallback`.

**Recommendation.** **(B)** — warn only. Friction is bad UX for
the user who knows what they're doing.

**Blocks.** M10 polish (cross-platform validation).

---

## Summary

| ID | Question | Severity | Blocks |
|---|---|---|---|
| Q3 | trainer-core extract or import | ✅ Superseded (D-T1) | — |
| Q5 | profile.toml mirror conflict | Critical | M3 |
| Q7 | env-var prefix verbosity | Critical | M1 |
| Q26 | doctr clone strategy | ✅ Superseded (D-T9) | — |
| Q1 | dnd-kit confirmation | Important | M4 |
| Q2 | recharts confirmation | Important | M6, M7 |
| Q11 | copy-to-datasets always-async | Important | M4 |
| Q12 | training queue cap | Important | M6 |
| Q15 | HF read/publish flag split | Important | M10, M11 |
| Q24 | build peer driver repo | Important | none |
| Q27 | pdomain-ocr-ops stdout event parser | Important | M6 progress |
| Q4 | typeface enum validation timing | Nice-to-have | M3 / M11 |
| Q6 | explicit sidecar_schema field | Nice-to-have | M7 |
| Q8 | HF publish path | Nice-to-have | M11 |
| Q9 | typeface classifier arch | Nice-to-have | M12 |
| Q10 | glyph classifier multi-head | Nice-to-have | M14 |
| Q13 | progress.jsonl cap | Nice-to-have | none |
| Q14 | parser_drift threshold | ✅ Superseded (re-spec) | — |
| Q16 | regression-alert spec location | Nice-to-have | none |
| Q17 | hf_default_owner default | Nice-to-have | M11 |
| Q18 | source weight normalization | Nice-to-have | M10 |
| Q19 | HF LFS quota handling | Nice-to-have | M11 |
| Q20 | persist event ring across restarts | Nice-to-have | none |
| Q21 | training subprocess daemonization | Nice-to-have | none |
| Q22 | persist banner dismissals | Nice-to-have | M8 |
| Q23 | command palette in v1 | Nice-to-have | M8 polish |
| Q25 | MPS slow-arch warning | Nice-to-have | M10 polish |

The two remaining **Critical** ones (Q5, Q7) are the only blockers
for starting M0 — Q3 and Q26 were resolved by the 2026-05-21
retirement re-spec. Q27 (the `pdomain-ocr-ops` stdout event parser) is a
cross-repo dependency for M6 live progress. Everything else can flow
under the spec author's recommendations until you say otherwise.
