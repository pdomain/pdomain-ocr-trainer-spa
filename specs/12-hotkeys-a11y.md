# 12 — Hotkeys and accessibility

Keybindings, focus management, ARIA conventions, kanban keyboard
operation.

> Required reading: [`03-frontend.md`](03-frontend.md),
> [`05-dataset-kanban.md`](05-dataset-kanban.md),
> [`13-driver-contract.md`](13-driver-contract.md).

---

## 1. Hotkeys library

`react-hotkeys-hook` everywhere. The `useHotkey` wrapper enforces:

- All bindings registered via the wrapper, **not** raw
  `useHotkeys`. The wrapper records to a global map for the
  `?` help dialog.
- A binding is scoped to a `scope` string. Switching scope on
  navigation tears down the previous map.
- `enableOnFormTags = false` by default; explicit opt-in per
  hotkey when needed (e.g. `Ctrl+S` in the run form).

---

## 2. Global hotkeys (scope `app`)

| Combo | Action | Notes |
|---|---|---|
| `?` | Open hotkey help dialog | Lists all active scopes' bindings. |
| `g p` | Go to Profiles | Two-key chord. |
| `g d` | Go to Datasets (active profile) | Falls back to `/profiles` if no active profile. |
| `g r` | Go to Runs | |
| `g m` | Go to Models | |
| `g e` | Go to Eval | |
| `g s` | Go to Settings | |
| `Ctrl/Cmd+K` | Open command palette | Deferred; see the [intent map](../docs/context/intent-map.md). |
| `Esc` | Close active dialog / clear selection | Dialog wins over selection. |

---

## 3. Page-scoped hotkeys

### 3.1 Datasets / kanban (scope `kanban`)

| Combo | Action |
|---|---|
| `j` / `k` | Move focus down / up within the focused column |
| `h` / `l` | Move focus left / right (column) |
| `x` | Toggle selection on focused chip |
| `Shift+ArrowDown` etc. | Range-extend selection |
| `Ctrl/Cmd+a` | Select all in focused column |
| `Esc` | Clear selection |
| `t` / `v` / `u` | Move selected chips to Train / Val / Unassigned |
| `Enter` | Open chip's detail (project ID page list, or crop preview) |
| `r` | Rescan (= scan endpoint) |
| `a` | Apply staged moves (= apply endpoint) |
| `d` | Discard staged moves |

`t` / `v` / `u` stage moves into client state (D-T23); they do
**not** hit the server — `a` (Apply) commits.

Focus model: each chip is a roving-tabindex `[role="listitem"]`
inside a `[role="list"]` per column. The column itself is
`[role="region" aria-label="Training" aria-keyshortcuts="j k h l"]`.
Keyboard drag-and-drop is provided by the `pdomain-ui` `KanbanBoard`
(D-T4) via dnd-kit's `KeyboardSensor`: `Space` to grab, arrows to
move, `Space` to drop, `Esc` to abort.

### 3.2 Run detail (scope `run-detail`)

| Combo | Action |
|---|---|
| `c` | Cancel run (only when running) |
| `o` | Open Model (only on success) |
| `e` | Open eval form |
| `/` | Focus log search |
| `Ctrl+End` | Jump to log tail and re-enable auto-scroll |
| `Ctrl+f` | Inline find-in-log |
| `s` | Toggle stdout/stderr view |
| `w` | Toggle log wrap |

### 3.3 Run form (scope `run-form`)

| Combo | Action |
|---|---|
| `Ctrl/Cmd+Enter` | Submit |
| `Esc` | Cancel form (with confirmation if dirty) |
| `Ctrl/Cmd+S` | Save defaults to profile |

### 3.4 Models page (scope `models-list`)

| Combo | Action |
|---|---|
| `Enter` | Open focused model |
| `r` | Rename model |
| `p` | Publish to HF (gated) |
| `Delete` | Delete model (confirm dialog) |

---

## 4. Conflict resolution

`useHotkey` rejects duplicate bindings within the same scope at
mount time (throws in dev, logs `console.error` in prod). Two
different scopes can share a key — only the active scope handles
it.

Native browser shortcuts (`Cmd+R`, `Cmd+W`, F-keys) are never
overridden.

---

## 5. Focus management

- Route changes restore focus to the first heading (`<h1>`) of the
  new page after the data is ready.
- Modal dialogs trap focus (the `pdomain-ui` dialog primitive enforces
  this). On close, focus returns to the trigger element.
- Toasts never steal focus.
- The kanban toolbar / footer buttons (`Rescan`, `Apply`,
  `Discard`) are reachable via `Tab` before the chips list.

---

## 6. ARIA / live regions

- `Toast` sonner-default `role="status" | "alert"`.
- `LogViewer` is `role="log" aria-live="polite"` while
  auto-scrolling; set `aria-live="off"` when the user pauses
  auto-scroll (avoid screen-reader flooding).
- `LossChart` is rendered inside a `<figure>` with a
  `<figcaption>` summarizing the latest values; the canvas itself
  has `role="img" aria-label="…"`. Below the chart, an
  off-screen `<table>` mirrors the data points so screen readers
  can read the metric history without consuming the canvas.
- `RunStatusBadge` has both colour and text — never colour alone.
- `JobsBadge` count is announced on change with
  `aria-live="polite"`.
- Drag-and-drop in the kanban announces "picked up <chip>",
  "moved to Training" via dnd-kit's screen-reader announcer.

---

## 7. Colour and contrast

- All status colours have a non-colour signifier (icon or text).
- The `pdomain-ui` `tokens.css` palette keeps WCAG AA contrast
  (≥ 4.5:1) on body text — no direct Tailwind (D-T19).
- Dark mode parity: every page tested in both themes; the test
  suite asserts no hard-coded colour outside the `pdomain-ui`
  `tokens.css` semantic tokens.

---

## 8. Help dialog (`?`)

`<HotkeyHelpDialog>` reads from the global registry kept by
`useHotkey`:

```
┌──────────────────────────────────────────┐
│  Keyboard shortcuts          [×]         │
├──────────────────────────────────────────┤
│  Global                                  │
│    ?           Show this dialog          │
│    g p / g d / g r / ...                 │
│  Datasets                                │
│    j / k       Move focus                │
│    t / v / u   Move selected chips       │
│    ...                                   │
│  Run detail                              │
│    c           Cancel run                │
│    /           Focus log search          │
│    ...                                   │
└──────────────────────────────────────────┘
```

Section visibility: only scopes that have at least one bound
hotkey on the current page render. The dialog itself is keyboard-
operable (`Tab` between sections, `Esc` to close).

---

## 9. Acceptance behaviour

1. From any page, press `?`. Dialog opens with current scope's
   hotkeys highlighted. `Esc` closes it.
2. Open the kanban. `Tab` lands on the Refresh button. `Tab`
   again → first chip. Arrow-key navigation moves the chip focus
   without scrolling the page.
3. With a chip focused, press `Space`. dnd-kit emits a "picked
   up" announcement. Arrow keys move the ghost between columns.
   `Space` again drops; the chip is staged client-side (no
   request). Press `a` to Apply.
4. With a run running, press `c`. Confirmation dialog appears,
   focus trapped. Confirm → cancel fires, focus returns to the
   `Cancel` button.
5. Toggle dark mode in the OS. Every page re-renders with
   high-contrast equivalents and no colour-only signifiers.

---

## 10. Citations

- Hotkey library + scope pattern: `pdomain-ocr-labeler-spa/specs/12-hotkeys-a11y.md`.
- dnd-kit accessibility: dnd-kit docs §Accessibility (KeyboardSensor).
- ARIA for chart canvases: WAI-ARIA Authoring Practices §Chart pattern.
