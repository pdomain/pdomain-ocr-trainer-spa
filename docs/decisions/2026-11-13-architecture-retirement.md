---
Status: active
Owner: CT
Created: 2026-11-13
Last verified: 2026-11-13
Kind: decision
---

# Retire superseded design stubs after architecture promotion

## Agent Index

- **Kind:** decision
- **Status:** active
- **Read when:** recovering a removed numbered spec or checking its replacement.
- **Search terms:** retirement, architecture, numbered specs, driver contract.

## Context

The 2026-11-12 migration captured shipped behavior in architecture and left
reviewed superseded stubs under `specs/`. Fresh source and test analysis on
2026-11-13 confirmed that those stubs carry no unique live requirements.
Both partial plans and the machine-parsed driver inventory still serve a purpose.

## Decision

Retire the twenty superseded stubs listed below. Preserve the driver contract
at `specs/13-driver-contract.md`, whose numbered headings and tables are input
to `tests/e2e/test_driver_contract.py`. Keep the M12 and review-fixes plans
partial: production classification and device mapping remain unfinished.

Promoted behavior is in [trainer workflows](../architecture/trainer-workflows.md),
[shell and jobs](../architecture/shell-and-jobs.md), and
[runs and evaluation](../architecture/runs-and-evaluation.md).
The other topic pages retain dataset, model, labeler and HF behavior. The
[roadmap](../roadmap.md) remains the backlog; retirement does not authorize
classifiers, a driver package, or a device mapping.

## Consequences

Git history preserves both the old full designs and the reviewed stubs.
Recover a stub from the promotion commit named below. Its historical full
body is available from the parent of `3a01156`. Live references point to
architecture; old decision-log references remain as historical evidence.

The index now covers `specs/`, including the retained driver contract.
No exclusion or weakened check hides the remaining documentation.

## Supersedes / Superseded-by

This retirement supersedes the live stub paths below, not the earlier decisions,
the partial plans, the roadmap, or the retained driver contract. The historical
2026-11-12 supersession record remains intact in
[the decision log](../context/decisions.md).

## Evidence

- `3a0115613fda814b989c566a52c1d8f2aa4cce5b` added the reviewed stubs and
  replacement architecture. Each removed spec had full metadata and an actual
  `Adversarial Review` record dated 2026-11-12.
- Promotion commit: `8e61500f1157514c3a304f1a98b1614c7a4d549f`.
- Code and tests are cited in the replacement architecture. Fresh independent
  analyzers inspected all fifty tracked Markdown documents in eight batches.
- `docgraph neighbors` checked every retirement path before deletion. The
  surviving contract is linked by the README, roadmap and shell architecture.
- The optional retirement planner deferred an existing unindexed source as
  `source_missing`. The direct governed retirement procedure was used instead;
  the engine did not apply this retirement.

## Retirement tombstones

### 2026-11-13 Retired: 00 — Overview

- Old path: `specs/00-overview.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [trainer-workflows](../architecture/trainer-workflows.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 01 — Data models

- Old path: `specs/01-data-models.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [profiles-datasets-and-models](../architecture/profiles-datasets-and-models.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 02 — Backend

- Old path: `specs/02-backend.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [trainer-workflows](../architecture/trainer-workflows.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 03 — Frontend

- Old path: `specs/03-frontend.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [shell-and-jobs](../architecture/shell-and-jobs.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 04 — Profiles and config

- Old path: `specs/04-profiles-and-config.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [profiles-datasets-and-models](../architecture/profiles-datasets-and-models.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 05 — Dataset kanban

- Old path: `specs/05-dataset-kanban.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [profiles-datasets-and-models](../architecture/profiles-datasets-and-models.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 06 — Training runs

- Old path: `specs/06-training-runs.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [runs-and-evaluation](../architecture/runs-and-evaluation.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 07 — Evaluation and metrics

- Old path: `specs/07-evaluation-and-metrics.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [runs-and-evaluation](../architecture/runs-and-evaluation.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 08 — Models

- Old path: `specs/08-models.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [profiles-datasets-and-models](../architecture/profiles-datasets-and-models.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 09 — Hugging Face integration

- Old path: `specs/09-hf-integration.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [huggingface](../architecture/huggingface.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 10 — Jobs and SSE

- Old path: `specs/10-jobs-and-sse.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [shell-and-jobs](../architecture/shell-and-jobs.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 11 — Notifications

- Old path: `specs/11-notifications.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [shell-and-jobs](../architecture/shell-and-jobs.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 12 — Hotkeys and accessibility

- Old path: `specs/12-hotkeys-a11y.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [shell-and-jobs](../architecture/shell-and-jobs.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 14 — Testing strategy

- Old path: `specs/14-testing.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [trainer-workflows](../architecture/trainer-workflows.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 15 — Deployment and dev

- Old path: `specs/15-deployment-dev.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [trainer-workflows](../architecture/trainer-workflows.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 16 — Milestones

- Old path: `specs/16-milestones.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [trainer-workflows](../architecture/trainer-workflows.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 17 — Decisions log

- Old path: `specs/17-decisions.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [trainer-workflows](../architecture/trainer-workflows.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 18 — Deferred HF datasets

- Old path: `specs/18-deferred-hf-datasets.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [huggingface](../architecture/huggingface.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: 19 — Deferred glyph classifier

- Old path: `specs/19-deferred-glyph-classifier.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [profiles-datasets-and-models](../architecture/profiles-datasets-and-models.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.

### 2026-11-13 Retired: Specs

- Old path: `specs/README.md`
- Outcome: superseded; reviewed stub deleted after promotion.
- Superseded by: [trainer-workflows](../architecture/trainer-workflows.md).
- Removal commit: RETIREMENT_COMMIT.
- Rationale kept: replacement architecture and the 2026-11-12 decision log.
- Remaining work: the roadmap and partial plans remain authoritative.
