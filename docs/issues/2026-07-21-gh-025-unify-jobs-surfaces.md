---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: issue
Level: I1
---

# Unify jobs surfaces: SSE toasts vs AppShell jobs dock

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-07-21
- **Resolution:** Open
- **Severity:** Medium — dual job-progress surfaces confuse operators
- **Affected version:** pdomain-ocr-trainer-spa master @ cutover 2026-07-21
- **Read when:** working on former GH #25, jobs dock, SSE notifications, or
  AppShell job progress
- **Search terms:** former GH #25, useNotificationStream, useTrainerJobs,
  jobs dock, SSE toasts, AppShell
- **Relates to:** [roadmap](../roadmap.md)

## Summary

After the AppShell migration, two job-progress surfaces coexist. SSE-driven
toasts come from `useNotificationStream`. The AppShell jobs dock is fed by
`useTrainerJobs` polling.

Product direction already leans toward **keeping both**:
[decisions.md](../context/decisions.md) (2026-07-14) records that the
notification stream drives transient notices and `GET /api/jobs` supplies the
dock because they serve different interaction needs. Residual open work is the
**implementation split** (poll vs push for the dock) and whether any toast
noise should still be trimmed.

Provenance: former GH #25. Roadmap priority: **Now**.

## Impact

- Operators can see job progress in two places with different update models
  (push toasts vs poll dock).
- New shell work can double-wire notifications if roles stay undocumented.

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

`useNotificationStream` remains the toast path. `useTrainerJobs` remains the
dock path. No single ownership decision is recorded in context docs.

## Root-cause hypotheses

1. **(Most likely) Deliberate dual UX, interim transport** — product keeps both
   surfaces; dock still polls while toasts use SSE because the dock landed on
   the jobs list API first.
2. **Missing SSE→dock adapter** — dock could subscribe to the same event stream
   without a second poller.
3. **Toast noise still too high** — dual by design may still need quieter
   completion/error rules so the dock stays primary for ongoing work.

## Defects to fix

1. **Confirm dual UX in architecture docs** — align trainer-workflows with
   decisions.md so agents do not “unify away” the dock or toasts by accident.
2. **Optional: feed dock from SSE** — if poll lag or double transport cost
   matters, share the notification stream into the dock without retiring toasts.

## Next steps

1. Treat dual surfaces as intentional unless owner reopens product direction.
2. Document toast vs dock roles in
   [trainer workflows](../architecture/trainer-workflows.md).
3. Only then consider SSE-fed dock or toast quieting as a tech follow-up.

## What is NOT broken (to scope the fix)

- Job execution itself (worker, API, SSE stream production).
- AppShell layout and compute panel wiring outside the progress dual-path.
- Profile / dataset / run CRUD unrelated to notification delivery.

## Resolution

_Open._ When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit here, move the README pointer to Resolved, and route
retirement through `doc-retirer`.
