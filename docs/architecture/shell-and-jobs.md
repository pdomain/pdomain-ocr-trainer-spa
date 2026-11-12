---
Status: active
Owner: CT
Created: 2026-11-12
Last verified: 2026-11-12
Kind: architecture
---

# Shell, jobs, and the client contract

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** changing the shell, job progress, banners, shortcuts, or
  stable routes.
- **Search terms:** AppShell, jobs dock, SSE, banners, driver contract,
  shortcuts

The React app is a pdomain-ui `AppShell` over the trainer routes.

Operators can see job progress today in the polling dock and the run-detail
event stream. The toast hook is not mounted.

No request handler calls `current_user` or reads `state.auth`. Bootstrap
stores `NoneAuth`. `NoneAuth.current_user` would return
`AuthedUser(id="local", roles=["admin"])` if a handler called it.

Hugging Face preview and publish return 400 `hf.auth_missing` when the token
path is missing. They do not consult that user.

## Routes, dock settings, and env.js flags

`/` redirects to `/profiles`. The router then declares:

- profiles
- profile detail
- dataset boards
- runs
- the new-run form
- run detail
- models
- model detail
- eval
- the eval result
- `/publish`

There is no `/settings` route and no `/datasets` route.

`trainerSettingsPanels.ts` adds a Compute panel after the built-in Appearance
panel on the utility-dock settings surface. The jobs list is a different
surface of that dock.

`/env.js` reports `driverContractVersion` 1, the app version, and three flags
the React app does not read: `enableTypefaceTraining`, `enableGlyphTraining`,
and `enableHfPublish`.

## Jobs API, the polling dock, and toasts

This app mounts its own jobs router. Suite mount from `pdomain-ops` does not
serve `/api/jobs`.

The routes are:

- `GET /api/jobs`
- `GET /api/jobs/active-count`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/events`
- `POST /api/jobs/{job_id}/cancel`

The list projects each ops job to `id`, `run_id`, `kind`, `state`,
`progress`, `error`, `started_at`, and `finished_at`.

The SSE route writes one `retry: 5000` frame (`_SSE_RETRY_MS`). It then
writes one frame per event. `id` is the sequence, `event` is the kind, and
`data` is JSON.

An integer `Last-Event-ID` skips sequences at or below that value. A
non-integer header is ignored, and the stream replays every event.

The stream does not write keepalive comments.

An unknown job returns 404 `job.unknown` before the body starts.

The dock in `useTrainerJobs` polls `GET /api/jobs` every 5 seconds.

The dock copies `progress` (0–1) into `pct` with no scale change. pdomain-ui
`JobRow` treats `pct` as 0–100, so a progress of 0.42 renders as 0.42%.

`cancelled` is sent as `failed`.

`pausable` is omitted. `JobRow` defaults it to true, so Pause and Resume
still show. `makeJobsProps` passes no pause handler.

Rows set `cancelable` to false.

The header pill uses that same poll.

The UI does not call `GET /api/jobs/active-count`.

Run detail subscribes with a local `EventSource` helper, not pdomain-ui
`useLongJob`.

Opening a dock row navigates to `/runs/` plus the row id.

That row id is the job id `j.id`. It is not the run id `run_id`.

`AppToaster` mounts one sonner toaster.

`useNotificationStream` would toast terminal job events. Its unit test covers
that. `App.tsx` does not call the hook.

Nothing in the running UI calls `emitToast`. A finished job does not toast.

## Banners, shortcuts, and loss charts

`BannerStack` loads `GET /api/banners`.

Dismissals that the stack allows are stored in `sessionStorage` for the tab.
They do not acknowledge labeler freshness.

The token banner fires only when `hf_token_path` is set and `exists()` is
false.

The token banner action href `/settings` and the fresh-labeled-pages banner
action href `/datasets` are not routes.

The disk banner fires when free space is under 5 percent
(`DISK_LOW_THRESHOLD = 0.05`). The probe walks up to an existing ancestor of
`shared_models_dir`. That banner sets `dismissible` to false.

The shortcut cheatsheet is the pdomain-ui `?` help. Chord navigation such as
`g p` is not registered.

The dataset page handles `r`, `a`, `d`, `t`, `v`, `u`, and Escape with its
own key listener.

The kanban chip handles Space, arrows while grabbed, Escape, and `x`.

Loss charts are the local SVG component `LossChart`. Recharts is not a
dependency.

## Driver contract the test still parses

[specs/13-driver-contract.md](../../specs/13-driver-contract.md) is still the
table that `tests/e2e/test_driver_contract.py` parses.

That test greps frontend source for the ids. It does not drive a browser.

Do not replace the table until the test reads the replacement.

A separate driver repository is not part of this app. See the
[roadmap](../roadmap.md).

## Code and tests checked

- Code: `frontend/src/App.tsx`, `frontend/src/shell/useTrainerJobs.ts`,
  `frontend/src/shell/trainerSettingsPanels.ts`,
  pdomain-ui `src/shell/JobRow.tsx` (pct is 0–100; omitted `pausable` defaults
  to true),
  `frontend/src/hooks/useNotificationStream.ts`,
  `frontend/src/components/AppToaster.tsx`,
  `frontend/src/components/BannerStack.tsx`,
  `frontend/src/shell/useTrainerShortcuts.ts`,
  `src/pdomain_ocr_trainer_spa/api/jobs.py`,
  `src/pdomain_ocr_trainer_spa/api/env_js.py`,
  `src/pdomain_ocr_trainer_spa/domain/banners.py`,
  `src/pdomain_ocr_trainer_spa/bootstrap.py`
- Tests: `tests/e2e/test_driver_contract.py`,
  `tests/integration/api/test_jobs.py`,
  `frontend/src/hooks/useNotificationStream.test.tsx`,
  `frontend/src/shell/useTrainerJobs.test.ts`
- Verified: 2026-11-12 by reading those files. Tests were not rerun.
