# 05 — Dataset kanban

The Datasets page is a 3-column kanban (Unassigned / Training /
Validation) for one `(profile, task)` pair. Drag-and-drop and
multi-select move project rows or individual page chips between
columns; a single explicit "Copy to Datasets" action then writes the
moves to disk.

> Required reading: [`01-data-models.md`](01-data-models.md)
> §2 (DatasetView, DatasetPageRef, DatasetCropRef),
> [`02-backend.md`](02-backend.md) §5.3,
> [`12-hotkeys-a11y.md`](12-hotkeys-a11y.md) §Kanban.

This spec covers detection + recognition. The classifier kanbans
(typeface, glyph) reuse the same component with task-specific
chip rendering — see §10.

---

## 1. Columns and what's in them

| Column id | Source | Render |
|---|---|---|
| `unassigned` | Labeler DocTR export root pages not yet copied to either split | "[export]" suffix on project row |
| `train` | Files already in `ml-training/<profile>/<task>/` | "[on disk]" suffix |
| `val` | Files already in `ml-validation/<profile>/<task>/` | "[on disk]" suffix |

`unassigned` may include pages that *also* exist on disk under a
different split (the legacy code highlights these in **yellow** as
"changed"; we keep that rule — see §6).

---

## 2. Wire model

```python
class KanbanView(BaseModel):
    profile: str
    task: TaskEnum
    columns: dict[Literal["unassigned", "train", "val"], KanbanColumn]
    include_detection: bool        # remembered toggle for the "Copy to Datasets" action
    include_recognition: bool

class KanbanColumn(BaseModel):
    rows: list[KanbanProjectRow]   # ordered by project_id

class KanbanProjectRow(BaseModel):
    project_id: str
    source: Literal["pending", "on_disk"]   # "pending" == from labeler export, "on_disk" == in this column already
    page_count: int
    is_changed: bool               # only meaningful for source=="pending"; True if a different version of these pages already exists in train|val
    style_tags: list[str]          # e.g. ["italics"]
    pages: list[KanbanPageChip]    # always populated for v1; if performance forces, lazy-load on expand later

class KanbanPageChip(BaseModel):
    key: str                       # opaque, scoped to (column, project, page_or_crop). Used by the SPA as the DnD id.
    page_name: str                 # for detection
    crop_name: str | None          # for recognition / classifier; null for detection
    label_text: str | None         # for recognition
    is_changed: bool
```

`key` shape: `<column>:<project_id>:<page_or_crop_name>`. Stable
across reloads; the move endpoints accept and emit these.

---

## 3. Endpoints

```
GET  /api/profiles/{profile}/datasets/{task}/kanban
     → KanbanView                                          (200)

POST /api/profiles/{profile}/datasets/{task}/scan
     → KanbanView                                          (200)
     # Forces a re-walk of the export root + on-disk dirs

POST /api/profiles/{profile}/datasets/{task}/move
     body: MoveRequest
     → KanbanView                                          (200)

POST /api/profiles/{profile}/datasets/{task}/include-toggles
     body: { include_detection: bool, include_recognition: bool }
     → KanbanView                                          (200)
     # Persists the two checkboxes to <app-data-root>/profiles/<name>/kanban_state.json

POST /api/profiles/{profile}/datasets/{task}/clear
     body: { column: "train" | "val" }
     → KanbanView                                          (200)
     # Removes all pages in that split (for this profile + task only)

POST /api/profiles/{profile}/datasets/{task}/copy-to-datasets
     → CopyResult{ copied: int, skipped: int, errors: [...] }
     # Persists the kanban moves to ml-training/ + ml-validation/ on disk
```

`MoveRequest` is the universal kanban move:

```python
class MoveRequest(BaseModel):
    from_column: Literal["unassigned", "train", "val"]
    to_column: Literal["unassigned", "train", "val"]
    items: list[MoveItem]

class MoveItem(BaseModel):
    kind: Literal["project", "page"]
    project_id: str
    page_or_crop_names: list[str] | None = None   # required if kind=="page"
```

Server semantics on `move`:

- Always validates `from_column`, `to_column`, and that the items
  exist in `from_column`.
- Mutates only the **in-memory kanban state** for this profile+task
  (an `ExportManager`-style staging buffer; see §5). Disk is
  untouched until `copy-to-datasets`.
- `unassigned → unassigned` is a no-op (200, returns current view).
- `unassigned → train|val` is a *staging* assignment.
- `train ↔ val` between on-disk pages is also staging — does **not**
  immediately rewrite disk; the move is applied on
  `copy-to-datasets` using `move_existing_page` semantics from
  legacy `ExportManager`.

---

## 4. `copy-to-datasets` semantics

Mirrors legacy `ExportManager.save_assignments(include_detection,
include_recognition)`:

1. For every staged unassigned → train|val assignment:
   - Copy the relevant labeler-export task subdirs into the target
     `ml-{training,validation}/<profile>/<task>/` directory.
   - Update the target `labels.json` (detection: bbox dict;
     recognition: text dict).
2. For every staged train ↔ val swap of on-disk pages:
   - `move_existing_page(name, from_split, to_split)` — atomic on
     POSIX (rename); two-phase on Windows (copy then delete) with
     a temp suffix to keep crashes safe.
3. Honours `include_detection` / `include_recognition` flags from
   the persisted `kanban_state.json`.
4. Returns counts and any per-item errors. Errors do not abort the
   whole batch — best-effort, partial-success.

The endpoint is a **synchronous** call (no `Job`) when total work is
< 30 items; for larger batches the SPA detects via response time and
optionally rewires through `Run` (kind=`copy-to-datasets`)
([Q11](../OPEN_QUESTIONS.md): always-async, or threshold?).

---

## 5. In-memory staging buffer

The legacy trainer uses `ExportManager` (in `dataset_store.py`) to
hold pending assignments in a Python dict between drag and "Copy
to Datasets". The SPA backend keeps the same idea, persisted across
restarts at:

```
<app-data-root>/profiles/<name>/kanban_state.json
{
  "task": "recognition",
  "version": 1,
  "pending_assignments": {
    "<project_id>:<page_name>": "train" | "val"
  },
  "moves_existing": [
    { "page_name": "...", "from": "train", "to": "val" }
  ],
  "include_detection": true,
  "include_recognition": true
}
```

Persisted on every `move` call. Cleared (with `pending_assignments
= {}`, `moves_existing = []`) on successful `copy-to-datasets`.
Stale entries (referring to a project_id no longer in the export
root, or a page no longer on disk) are silently dropped on next
`scan`.

---

## 6. The "changed" highlight

A pending page is `is_changed = True` when:

- Its filename matches a page already on disk under
  `ml-training/<profile>/<task>/` or `ml-validation/.../`, **and**
- The bbox-set or label text differs from the on-disk version.

Frontend renders changed pages with a yellow background (matching
the legacy `bg-yellow-100`). Hovering the chip shows a diff tooltip
("3 bboxes added, 1 removed" / "label changed: 'old' → 'new'").
The diff payload is part of the chip:

```python
class KanbanPageChip(BaseModel):
    ...
    change_summary: str | None = None   # e.g. "3 bboxes added, 1 removed"
```

---

## 7. Selection and DnD UX

- Entire project row is draggable as a unit. Drop on a column moves
  every chip in that row.
- Individual chips are draggable individually.
- Multi-select on chips (`train` and `val` columns; not in
  `unassigned` per legacy):
  - Plain click → selects only this chip; clears the rest.
  - `Cmd/Ctrl-click` → toggles this chip in/out.
  - `Shift-click` → range-selects from anchor to this chip.
  - Anchor is the last plain-clicked chip per `(column, project_id)`.
- Dragging any selected chip drags the entire selection (per legacy
  `existing_page` list-mode at `dataset_ui.py:248-261`).
- Drop targets accept any subset; the move endpoint computes the
  delta server-side.

Implementation: **dnd-kit** for drag/drop with a custom collision
detector that snaps to the nearest column. Selection state lives in
`SelectionStore` (see [`03-frontend.md`](03-frontend.md) §3.3).

Keyboard a11y: see [`12-hotkeys-a11y.md`](12-hotkeys-a11y.md).

---

## 8. Toolbar and footer

- Header row of the kanban shows:
  - `[Refresh]` button → `POST /scan`. Replaces in-memory + reloads.
  - `[ ] Include detection` / `[ ] Include recognition` checkboxes.
  - Filter input: free-form substring filter on `project_id`.
  - Style-tag dropdown: filters chips by `style_tags`. Defaults to
    "all".
  - "Showing N of M pages" counter.
- Footer of the kanban shows:
  - `[Clear train]` / `[Clear val]` buttons (matching legacy
    `clear_split()`). Confirm dialog ("Remove N pages from the
    Training split? Their files will be deleted.").
  - `[Copy to Datasets]` primary action button.
  - Status message line (e.g. "Copied 12 export task(s) into
    'clogaelach' datasets.").

---

## 9. Optimistic UI

`move` is optimistic: the SPA reorders chips locally and fires the
PATCH. On failure, it rolls back and toasts the error.

`copy-to-datasets` is **not** optimistic — chips that move from
`unassigned` to a split column show a "copying" spinner per row
until the response arrives.

---

## 10. Classifier kanbans (typeface, glyph)

For `task in {typeface-classification, glyph-classification}`, the
chip is a **crop**, not a page:

- `KanbanPageChip.crop_name` populated; `page_name` is the parent
  detection page.
- `label_text` is repurposed:
  - For typeface: the typeface enum value.
  - For glyph: a compact summary like `ct,long_s` of which features
    are positive.
- Multi-select uses `crop_name` instead of `page_name` in the
  `MoveItem.page_or_crop_names` list.

The kanban view-mode toggle (see [`12-hotkeys-a11y.md`](12-hotkeys-a11y.md))
has a "thumbnail strip" mode for crop-heavy datasets that previews
each chip's image (lazy-loaded via
`GET /api/profiles/{p}/datasets/{task}/crop-image?key=...`).

---

## 11. Acceptance behaviour

1. Drop a labeler export under `<labeler-export-root>/myproj/`. Hit
   the kanban for `(all, recognition)`. The project row appears in
   `unassigned` with `[export]`.
2. Drag the project row to `train`. The row moves; status footer
   updates count. Disk is unchanged.
3. Click `Copy to Datasets`. The row's chips disappear from
   `unassigned` and appear under `train` with `[on disk]`. Files
   exist under `ml-training/all/recognition/`.
4. Click `Refresh`. State unchanged.
5. Shift-click on three chips in `train`, drag any one to `val`.
   All three move (in-memory). `Copy to Datasets` writes the swap.
6. `Clear val` confirms with the page count. After confirm, all
   `val` rows disappear and their files are deleted.

---

## 12. Citations

- Legacy column defs: `pd-ocr-trainer/src/pd_ocr_trainer/dataset_ui.py:13-17`.
- Drag/drop dispatch: `dataset_ui.py:99-135`.
- Multi-select rules: `dataset_ui.py:61-97`.
- Existing-pages render + multi-select drag: `dataset_ui.py:230-262`.
- `Refresh` / `Copy to Datasets` actions: `dataset_ui.py:288-318`.
- ExportManager save semantics: `dataset_store.py:300-560` (search
  for `save_assignments`, `assign`, `assign_page`, `move_existing_page`).
