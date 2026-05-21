# 05 — Dataset kanban

The Datasets page is a 3-column kanban (Unassigned / Training /
Validation) for one `(profile, task)` pair. Drag-and-drop and
multi-select rearrange project rows and page chips between columns;
the rearrangement is **staged client-side** and committed atomically
by an explicit "Apply" action.

> Required reading: [`01-data-models.md`](01-data-models.md)
> §2 (DatasetView, DatasetPageRef, DatasetCropRef),
> [`02-backend.md`](02-backend.md) §6.3,
> [`12-hotkeys-a11y.md`](12-hotkeys-a11y.md) §Kanban.
>
> **Re-spec note (2026-05-21).** Rewritten onto the `pd-ui`
> `KanbanBoard` component (D-T4) and the staged-then-applied
> dataflow (D-T23). The kanban is no longer SPA-local, and there is
> no per-drag `move` endpoint or server-side staging buffer — drags
> mutate client state only, and one batch `apply` endpoint commits.

This spec covers detection + recognition. The classifier kanbans
(typeface, glyph) reuse the same component with task-specific chip
rendering — see §10.

---

## 1. Columns and what's in them

| Column id | Source | Render |
|---|---|---|
| `unassigned` | Labeler DocTR export-root pages not yet copied to either split | "[export]" suffix on project row |
| `train` | Files already in `<ml_training_dir>/<profile>/<task>/` | "[on disk]" suffix |
| `val` | Files already in `<ml_validation_dir>/<profile>/<task>/` | "[on disk]" suffix |

`unassigned` may include pages that *also* exist on disk under a
split (the legacy code highlights these **yellow** as "changed"; we
keep that rule — see §6).

---

## 2. Wire model

`KanbanView` is the **committed server truth** — the state on disk
plus the export root, as last scanned. Staged rearrangement lives in
client React state layered over it (§5); the server only ever sees a
full `apply`.

```python
class KanbanView(BaseModel):
    profile: str
    task: TaskEnum
    columns: dict[Literal["unassigned", "train", "val"], KanbanColumn]
    include_detection: bool        # persisted toggle for `apply`
    include_recognition: bool

class KanbanColumn(BaseModel):
    rows: list[KanbanProjectRow]   # ordered by project_id

class KanbanProjectRow(BaseModel):
    project_id: str
    source: Literal["pending", "on_disk"]   # "pending" == from labeler export
    page_count: int
    is_changed: bool               # only for source=="pending"; see §6
    style_tags: list[str]          # e.g. ["italics"]
    pages: list[KanbanPageChip]

class KanbanPageChip(BaseModel):
    key: str                       # opaque, stable; the DnD id and the apply id
    page_name: str                 # for detection
    crop_name: str | None          # for recognition / classifier; null for detection
    label_text: str | None         # for recognition
    is_changed: bool
    change_summary: str | None = None   # e.g. "3 bboxes added, 1 removed" — see §6
```

`key` shape: `<project_id>:<page_or_crop_name>`. Stable across
reloads and across re-scans for the same item; `apply` accepts these
keys.

---

## 3. Endpoints

```
GET  /api/profiles/{profile}/datasets/{task}/kanban
     → KanbanView                                          (200)

POST /api/profiles/{profile}/datasets/{task}/scan
     → KanbanView                                          (200)
     # Forces a re-walk of the export root + on-disk dirs

POST /api/profiles/{profile}/datasets/{task}/include-toggles
     body: { include_detection: bool, include_recognition: bool }
     → KanbanView                                          (200)

POST /api/profiles/{profile}/datasets/{task}/apply
     body: ApplyAssignmentRequest
     → KanbanView                                          (200)
     # Commits the full staged target-split assignment to disk
```

There is **no** `/move`, `/clear`, or `/copy-to-datasets` endpoint —
all rearrangement is client-side staging committed by `/apply`
(D-T23). Clearing a split is just staging every chip in it to
`unassigned` and applying.

`ApplyAssignmentRequest` is the whole target assignment, not a
delta:

```python
class ApplyAssignmentRequest(BaseModel):
    assignments: list[AssignmentEntry]

class AssignmentEntry(BaseModel):
    key: str                                        # KanbanPageChip.key
    target_split: Literal["unassigned", "train", "val"]
```

The client sends an entry for **every chip whose staged column
differs from its committed column** (unchanged chips are omitted).
The server diffs each entry against current disk state and performs
the minimal set of copies / moves / deletions.

---

## 4. `apply` semantics

`apply` is the single atomic commit, mirroring legacy
`ExportManager.save_assignments` + `move_existing_page`:

1. **`unassigned → train|val`** — copy the labeler-export task
   subdirs into `<ml_{training,validation}_dir>/<profile>/<task>/`
   and update the target `labels.json`.
2. **`train ↔ val`** of an on-disk page — `move_existing_page(name,
   from_split, to_split)`: atomic rename on POSIX, two-phase
   copy+delete on Windows with a temp suffix for crash safety.
3. **`train|val → unassigned`** — delete the page's files from that
   split's `<task>/` dir and prune its `labels.json` entry.
4. Honours the persisted `include_detection` / `include_recognition`
   flags.
5. Returns the freshly re-scanned `KanbanView`. Per-item errors do
   not abort the batch — best-effort, partial success; failed keys
   are reported (see below).

`apply` is **synchronous** (no job). Even a large reassignment is
file copies/renames on a local disk — fast enough not to need the
`LongJobRunner`. If a future profiling pass shows otherwise this can
move to a job, but core parity keeps it inline.

On partial failure the response is still `200` with the re-scanned
view; failed keys surface in a `X-Apply-Errors` response header
carrying a JSON list `[{key, error}]`, which the SPA renders as a
toast. A fully-failed `apply` (no key succeeded) is `409
dataset.apply_failed` with the same detail in the `ErrorEnvelope`.

---

## 5. Staging is client-side

There is **no** server-side staging buffer and no
`kanban_state.json` pending-assignments file. Staged moves live in
the `KanbanBoard`'s React state for the current tab only (D-T13,
D-T23):

- Each drag / multi-select move updates the staged column of the
  affected chip keys in client state. No request is sent.
- A pending-diff indicator shows how many chips differ from the
  committed `KanbanView` ("12 pending moves").
- **Apply** → `POST .../apply` with the diff; on `200` the staged
  overlay is replaced by the returned `KanbanView`.
- **Discard** → drop the staged overlay; re-render the committed
  `KanbanView`. No request.

The only persisted kanban state is the two include-toggles, written
server-side by `POST .../include-toggles` to
`<app_data_root>/profiles/<name>/kanban_state.json`:

```json
{ "version": 2, "include_detection": true, "include_recognition": true }
```

Two tabs can stage divergently until one applies; this is the
accepted trade-off of D-T13 (UI focus lives on the frontend). A
`scan` or a fresh `kanban` GET always returns committed truth.

---

## 6. The "changed" highlight

A pending (`unassigned`) page is `is_changed = True` when:

- Its filename matches a page already on disk under
  `<ml_training_dir>/<profile>/<task>/` or the validation dir, **and**
- The bbox-set (detection) or label text (recognition) differs from
  the on-disk version.

The `KanbanBoard` renders changed chips with a warning background
(`tokens.css` warning surface — see [`03-frontend.md`](03-frontend.md)).
Hovering shows `change_summary` as a tooltip ("3 bboxes added, 1
removed" / "label changed: 'old' → 'new'"). `change_summary` is
computed server-side and carried on the chip (§2).

---

## 7. The `pd-ui` `KanbanBoard` component

The kanban is the `pd-ui` `KanbanBoard` / `KanbanColumn` / `PageChip`
component family (D-T4) — not SPA-local. The SPA composes it; pd-ui
owns drag/drop, multi-select, and a11y.

- DnD: `@dnd-kit` inside pd-ui — `PointerSensor` for mouse,
  `KeyboardSensor` for a11y. A custom collision detector snaps to
  the nearest column.
- A whole project row drags as a unit; individual chips drag
  individually.
- Multi-select on chips (in `train` / `val`; not `unassigned`, per
  legacy):
  - Plain click → select only this chip.
  - `Cmd/Ctrl-click` → toggle this chip.
  - `Shift-click` → range-select from the anchor.
  - Anchor = last plain-clicked chip per `(column, project_id)`.
- Dragging any selected chip drags the whole selection.

The SPA supplies the `KanbanView` data, the staged-overlay state,
and an `onStage(moves)` callback; `pd-ui` renders and reports moves.
Selection state is internal to the `KanbanBoard`. Keyboard a11y:
[`12-hotkeys-a11y.md`](12-hotkeys-a11y.md).

---

## 8. Toolbar and footer

Header row (SPA-composed, around the `pd-ui` board):

- `[Rescan]` → `POST .../scan`. Discards the staged overlay after
  confirming if there are pending moves.
- `[ ] Include detection` / `[ ] Include recognition` — `pd-ui`
  checkboxes; each change fires `POST .../include-toggles`.
- Filter input: substring filter on `project_id`.
- Style-tag dropdown (`pd-ui Select`): filters chips by `style_tags`;
  default "all".
- "Showing N of M pages" counter.

Footer:

- Pending-diff indicator ("12 pending moves" / "No pending changes").
- `[Discard]` — drops the staged overlay (disabled when none).
- `[Apply]` — primary action; `POST .../apply` (disabled when no
  pending moves). A staged move that empties a split shows a confirm
  dialog ("Apply will remove N pages from Training — their files
  will be deleted.").
- Status message line (e.g. "Applied — 12 pages copied into
  'clogaelach' / recognition.").

---

## 9. UI behaviour during staging and apply

- Drags are **purely client-side** — instant, no spinner, no
  request, no rollback path (nothing to roll back).
- `Apply` shows a button-level busy state until the `200`; on
  success the board re-renders from the returned `KanbanView`; on
  partial failure the toast lists failed keys (§4) and the board
  shows post-apply truth (succeeded moves committed, failed ones
  back in their committed column).
- `Discard` and `Rescan` are instant client re-renders (Rescan after
  its GET resolves).

---

## 10. Classifier kanbans (typeface, glyph)

For `task in {typeface-classification, glyph-classification}` the
chip is a **crop**, not a page:

- `KanbanPageChip.crop_name` populated; `page_name` is the parent
  detection page.
- `label_text` is repurposed: the typeface enum value (typeface), or
  a compact positive-feature summary like `ct,long_s` (glyph).
- `key` uses `crop_name` as the item segment.

The `pd-ui` `KanbanBoard` has a "thumbnail strip" view mode for
crop-heavy datasets that previews each chip's image, lazy-loaded via
`GET /api/profiles/{p}/datasets/{task}/crop-image?key=...`.

---

## 11. Acceptance behaviour

1. Drop a labeler export under `<labeler-export-root>/myproj/`. Open
   the kanban for `(all, recognition)`. The project row appears in
   `unassigned` with `[export]`.
2. Drag the row to `train`. The row moves instantly; the footer
   shows "N pending moves". No request fired; disk unchanged.
3. Click `Apply`. The row's chips move under `train` with
   `[on disk]`; files exist under `<ml_training_dir>/all/recognition/`;
   footer shows "No pending changes".
4. Shift-click three chips in `train`, drag one to `val`. All three
   stage. `Apply` performs the swap via `move_existing_page`.
5. Stage every chip out of `val` to `unassigned`, `Apply`. The
   confirm dialog shows the page count; on confirm the `val` files
   are deleted.
6. Stage a move, click `Discard` — the board reverts to committed
   truth with no request.
7. `Rescan` returns committed truth and discards any staged overlay
   after confirmation.

---

## 12. Citations

- Legacy column defs: `pd-ocr-trainer/src/pd_ocr_trainer/dataset_ui.py:13-17`.
- Multi-select rules: `dataset_ui.py:61-97`.
- Existing-pages render + multi-select drag: `dataset_ui.py:230-262`.
- `ExportManager` save / move semantics: `pd-ocr-training/pd_ocr_training/datasets.py:242-609`
  (`save_assignments`, `move_existing_project`, `move_existing_page`).
- `KanbanBoard` component contract: `pd-ui` docs (D-T4).
