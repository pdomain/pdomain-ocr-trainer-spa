# 13 — Driver contract

`data-testid` and URL invariants for any future Playwright driver
agent (analogous to `pd-ocr-labeler-driver`). The trainer-spa does
not yet have a peer driver, but we lock the contract here so one
can be built later without renames.

> Required reading: [`03-frontend.md`](03-frontend.md),
> [`05-dataset-kanban.md`](05-dataset-kanban.md),
> [`06-training-runs.md`](06-training-runs.md).

---

## 1. Why this exists

The labeler-spa proved the value of a stable test-id contract:
the driver agent can drive the running UI without scraping
classnames, and a CI conformance test fails any rename. We adopt
the same pattern here from M0 onward.

The contract has two parts:

1. **`data-testid` invariants** — every interactive element on
   every page has a stable id, machine-grep-able, never auto-
   generated. ([Q24](../OPEN_QUESTIONS.md): build a peer driver
   repo too?)
2. **URL invariants** — every entity has a stable canonical URL.
   Deep-linking from external sources (a TODO list, a notification,
   a slack paste) must keep working across SPA versions.

---

## 2. URL invariants

| URL pattern | Stability |
|---|---|
| `/profiles` | **Stable.** Profile list. |
| `/profiles/{name}` | **Stable.** Profile detail. `name` is the normalized form. |
| `/profiles/{name}/datasets/{task}` | **Stable.** Kanban for this profile + task. |
| `/runs` | **Stable.** Run list. |
| `/runs/{run_id}` | **Stable.** Run detail. `run_id` is the ULID; never a slug. |
| `/models` | **Stable.** Model list. |
| `/models/{name}` | **Stable.** Model detail; `name` is the full prefixed model name. |
| `/eval` | **Stable.** Eval form. |
| `/eval/{run_id}/result` | **Stable.** Eval result page. |
| `/publish` | **Stable.** Publish form. |
| `/settings` | **Stable.** Read-only settings view. |

Query params:

- `?compare=run_id,run_id,...` on `/eval/.../result` — stable.
- `?profile=&task=&status=` filters on `/runs` — stable; new
  filters can be added but never silently rename.

URL changes outside this contract require an ADR in
[`17-decisions.md`](17-decisions.md).

---

## 3. data-testid conventions

- **kebab-case.** Always.
- **Hierarchical.** Outer container's testid is a prefix of
  contained interactive elements: `kanban-column-train` →
  `kanban-column-train-chip-projID-page`.
- **Stable across renders.** Never include random ids, indexes,
  or Date.now()-derived values in a testid.
- **Required on every interactive element.** Buttons, inputs,
  links, drag handles, drop zones.
- **Optional on purely presentational elements.** Headings,
  labels, decorative icons. (But headings that anchor a section
  do get testids if a driver might wait on the section.)

A linter rule (`eslint-plugin-testing-library` custom rule) flags
buttons / inputs / `<a>` without a `data-testid`.

---

## 4. Inventory by page

### 4.1 App chrome

| testid | Element |
|---|---|
| `header-bar` | Top header container |
| `header-app-version` | Version badge |
| `header-profile-selector` | Profile combobox button |
| `header-profile-selector-option-{name}` | Profile combobox menu items |
| `header-jobs-badge` | Jobs count badge |
| `header-help-button` | Opens hotkey help |
| `sidebar-nav` | Sidebar container |
| `sidebar-nav-{section}` | Each link (`profiles`, `datasets`, `runs`, `models`, `eval`, `publish`, `settings`) |
| `banner-{id}` | One per active banner (id from `Banner.id`) |
| `banner-{id}-action` | Banner action button |
| `banner-{id}-dismiss` | Dismiss button |
| `toast-{id}` | One per active toast (sonner generates id; we re-export it) |

### 4.2 Profiles page

| testid | Element |
|---|---|
| `profiles-page` | Page root |
| `profiles-new-button` | Open create dialog |
| `profiles-table` | Table |
| `profiles-row-{name}` | Each row |
| `profiles-row-{name}-edit` | Edit button |
| `profiles-row-{name}-delete` | Delete button |
| `profiles-edit-dialog` | Dialog root (in create or edit mode) |
| `profiles-edit-dialog-name` | Name input |
| `profiles-edit-dialog-display-name` | Display name input |
| `profiles-edit-dialog-language` | Language combobox |
| `profiles-edit-dialog-typeface` | Typeface select |
| `profiles-edit-dialog-submit` | Save button |
| `profiles-edit-dialog-cancel` | Cancel button |

### 4.3 Datasets / kanban

| testid | Element |
|---|---|
| `kanban-page` | Page root |
| `kanban-task-tabs` | Detection / Recognition / Typeface / Glyph tabs |
| `kanban-task-tab-{task}` | One per tab |
| `kanban-toolbar-rescan` | Rescan button |
| `kanban-toolbar-include-detection` | Detection checkbox |
| `kanban-toolbar-include-recognition` | Recognition checkbox |
| `kanban-toolbar-filter-input` | project_id substring filter |
| `kanban-toolbar-style-tag-filter` | Style-tag dropdown |
| `kanban-column-{column}` | `column ∈ unassigned, train, val` |
| `kanban-column-{column}-row-{project}` | Project row in this column |
| `kanban-column-{column}-row-{project}-handle` | Drag handle for the whole project row |
| `kanban-column-{column}-chip-{project}-{name}` | Page or crop chip |
| `kanban-footer-pending-count` | Pending-moves indicator |
| `kanban-footer-discard` | Discard staged moves |
| `kanban-footer-apply` | Primary apply button |
| `kanban-footer-status` | Status text |

The kanban chrome is composed around the `pd-ui` `KanbanBoard`
component (D-T4); these testids are the SPA's stable contract
regardless of the underlying pd-ui markup.

### 4.4 Run detail

| testid | Element |
|---|---|
| `run-detail-page` | Page root |
| `run-detail-status-badge` | Status badge |
| `run-detail-progress-bar` | Progress bar |
| `run-detail-cancel` | Cancel button (only when running) |
| `run-detail-open-model` | Open Model button (only on success) |
| `run-detail-open-eval` | Open Eval button |
| `run-detail-args-summary` | Args summary block |
| `run-detail-loss-chart` | Loss chart container |
| `run-detail-log-viewer` | Log viewer container |
| `run-detail-log-stream-toggle` | stdout/stderr toggle |
| `run-detail-log-autoscroll-toggle` | Auto-scroll toggle |
| `run-detail-log-wrap-toggle` | Wrap toggle |
| `run-detail-log-search` | Find-in-log input |
| `run-detail-log-line-{n}` | One per visible line (virtualized) |
| `run-detail-loss-chart-empty` | Empty-state placeholder (no metrics yet) |
| `run-detail-loading` | Loading placeholder |
| `run-detail-error` | Error placeholder |

### 4.4a Run list

| testid | Element |
|---|---|
| `run-list-page` | Page root |
| `run-list-refresh` | Refresh button |
| `run-list-filter-profile` | Profile substring filter input |
| `run-list-filter-status` | Status filter dropdown |
| `run-list-table` | Run table |
| `run-list-row-{run_id}` | One row per run |
| `run-list-row-{run_id}-status` | Row status badge |
| `run-list-row-{run_id}-link` | Row model-name link to `/runs/{run_id}` |
| `run-list-empty` | Empty-state placeholder |
| `run-list-loading` | Loading placeholder |
| `run-list-error` | Error placeholder |

### 4.4b New run form

| testid | Element |
|---|---|
| `new-run-page` | Page root |
| `new-run-profile` | Profile selector |
| `new-run-task` | Task selector |
| `new-run-qualifier` | Model-name qualifier input |
| `new-run-args-field-{key}` | One per training-args field (RunArgsEditor) |
| `new-run-start` | Start-run button |
| `new-run-error` | Form-level error block |

### 4.5 Models page + detail

| testid | Element |
|---|---|
| `models-page` | Page root |
| `models-table` | Table |
| `models-row-{name}` | Row |
| `models-row-{name}-rename` | Rename button |
| `models-row-{name}-publish` | Publish button (gated) |
| `models-row-{name}-delete` | Delete button |
| `models-detail-page` | Page root |
| `models-detail-sidecar-json` | Sidecar JSON viewer |
| `models-detail-eval-summary` | Best-eval summary |
| `models-detail-rename-dialog` | Rename dialog |
| `models-detail-rename-input` | New-name input |
| `models-detail-publish-dialog` | Publish dialog |
| `models-detail-publish-repo` | Repo input |
| `models-detail-publish-visibility-{value}` | Visibility radios (`private`, `public`) |
| `models-detail-publish-submit` | Submit |

### 4.6 Eval form + result

| testid | Element |
|---|---|
| `eval-form-page` | Page root |
| `eval-form-profile` | Profile combobox |
| `eval-form-task-{task}` | Task radios |
| `eval-form-model` | Model dropdown |
| `eval-form-source-{kind}` | Validation-source radios |
| `eval-form-slice-glyph-features` | Slice toggle |
| `eval-form-persist-predictions` | Persist toggle |
| `eval-form-submit` | Run eval |
| `eval-result-page` | Result page root |
| `eval-result-overall-cer` | Overall CER metric |
| `eval-result-overall-wer` | Overall WER metric |
| `eval-result-slice-{feature}` | One row per slice (`feature` is the encoded slice id) |
| `eval-result-download-json` | Download JSON button |
| `eval-result-download-md` | Download Markdown button |
| `eval-result-compare` | Open compare dialog |

---

## 5. Conformance test

A single Playwright spec, `tests/e2e/test_driver_contract.py`,
exercises every URL above and asserts the listed testids exist.
The driver contract is **what the conformance test passes**.

If a code change forces a testid rename, the spec change is part
of the same PR; CI fails on diff otherwise.

---

## 6. Versioning

The contract is versioned via `__APP_ENV__.driverContractVersion`,
exposed in `/env.js`. Bumping is a breaking change requiring a
notice in `17-decisions.md`. Drivers that pin a contract version
can refuse to operate against a newer SPA until the driver is
updated.

Initial version: `1`.

---

## 7. Citations

- Contract pattern: `pd-ocr-labeler-spa/specs/13-driver-contract.md`.
- Driver agent precedent: `pd-ocr-labeler-driver` (Playwright MCP-
  driven mechanical pre-pass agent).
