---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-11-13
Kind: issue
Level: I1
---

# Unify jobs surfaces: SSE toasts vs AppShell jobs dock

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-11-13
- **Resolution:** Open
- **Severity:** Medium — the toast hook is unmounted while the dock polls
- **Affected version:** pdomain-ocr-trainer-spa master @ cutover 2026-07-21
- **Read when:** working on former GH #25, jobs dock, SSE notifications, or
  AppShell job progress
- **Search terms:** former GH #25, useNotificationStream, useTrainerJobs,
  jobs dock, SSE toasts, AppShell
- **Relates to:** [roadmap](../roadmap.md)

## Summary

The jobs dock polls `GET /api/jobs` from `useTrainerJobs`. Run detail opens
the job SSE stream. `useNotificationStream` would toast terminal events, and
its unit test covers that, but `App.tsx` does not mount the hook and nothing
calls `emitToast`. Terminal toasts do not fire.

The 2026-07-14 decision said the notification stream drives transient notices.
That claim was corrected on 2026-11-12 in
[decisions.md](../context/decisions.md). Do not add a third progress surface.
The open choice is to mount the existing hook or delete it. An SSE-fed dock
is not required.

Provenance: former GH #25. Still open on the
[remaining-work list](../roadmap.md). Current behavior is in
[shell, jobs, and the client contract](../architecture/shell-and-jobs.md).

## Impact

- The dock polls while run detail consumes SSE. Neither proves that terminal
  toast notifications are delivered.
- The unused notification hook can be mounted twice or misunderstood unless
  the owner chooses whether to mount it or remove it.

## Environment / versions

```text
repo: pdomain/pdomain-ocr-trainer-spa
surfaces: frontend/src/hooks/useNotificationStream.ts
          frontend/src/shell/useTrainerJobs.ts
origin: Track A / Milestone F (pdomain-ui adoption)
```

## Evidence

### 1. Original issue scope

Former GH #25 described the dual surfaces as a deliberate Track A follow-on,
not a regression of the AppShell migration itself.

### 2. Current code still splits channels

`useTrainerJobs` polls the dock. Run detail opens the job SSE stream.
`useNotificationStream` has isolated unit tests but is not mounted by
`App.tsx`. The 2026-11-12 correction in the decision log supersedes the old
claim that terminal toasts already fire.

## Root-cause hypotheses

1. **Unconnected hook** — the toast helper is tested in isolation but has no
   application call site.
2. **Stale role description** — the earlier dual-surface description treated
   a proposed notification path as mounted behavior.

## Defects to fix

1. Decide whether to mount or remove the existing notification hook. This is
   an owner choice; an SSE-fed dock is not a requirement.

## Next steps

1. Confirm the mount-or-remove decision.
2. Implement only that choice and verify its terminal-event behavior.
3. Keep the polling dock and run-detail stream documented as separate paths.

## What is NOT broken (to scope the fix)

- Job execution itself (worker, API, SSE stream production).
- AppShell layout and compute panel wiring outside the progress dual-path.
- Profile / dataset / run CRUD unrelated to notification delivery.

## Resolution

_Open._ When this issue is fixed, route it through `doc-retirer` with the resolving
commit and evidence. Promote durable behavior, update inbound references,
remove the live README pointer, and append a tombstone to the decision log.
Resolved reports are deleted; there is no resolved index to maintain.
