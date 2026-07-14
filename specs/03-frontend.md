# 03 — Frontend (React/Vite/TS on pdomain-ui)

The SPA half of `pdomain-ocr-trainer-spa`. Built with Vite, served from the
FastAPI wheel in production, served via the Vite dev-server with an
`/api` proxy in development.

This spec covers the **shell**: routing, state stores, generated API
client, app chrome, and the page tree — and maps every legacy
`pdomain-ocr-training` NiceGUI element to a component. Per-feature specs
deepen each piece.

> Required reading: [`00-overview.md`](00-overview.md),
> [`02-backend.md`](02-backend.md), [`17-decisions.md`](17-decisions.md).

---

## 1. Component strategy — pdomain-ui first

The frontend is built on the shared **`pdomain-ui`** component library
(`@pdomain/pdomain-ui`, consumed from the `pdomain-index-npm` registry).
No Tailwind, no shadcn/ui — pdomain-ui supplies the design tokens
(`tokens.css` / `primitives.css`), primitives, and app shell.
([D-T19](17-decisions.md))

**Every interactive element of the legacy trainer maps to a pdomain-ui
component** (table in §6). Two component families needed by the trainer
do not yet exist in pdomain-ui and are added to it
([D-T4](17-decisions.md)) rather than built SPA-local:

- `KanbanBoard` / `KanbanColumn` / `PageChip` — drag-and-drop board.
- `LogViewer` — virtualized streaming-text viewer.
- `Field` / `FieldRow` — labelled form-row primitive.
- `JobStatusPip` — job-state pip.

These are tracked as cross-repo additions to the `pdomain-ui` spec; the
trainer-spa kanban/log/config milestones depend on them being built
first (see [`16-milestones.md`](16-milestones.md)).

Only two components stay **SPA-local** — both app-specific composition,
not reusable primitives:

- `LossChart` — a thin `recharts` wrapper over a run's `progress.jsonl`.
- `ModelExportPanel` — the model-name + export controls in run detail.

---

## 2. Project layout

<!-- markdownlint-disable MD013 -->

```text
frontend/
├── package.json
├── index.html             # loads /env.js then /src/main.tsx
├── vite.config.ts         # @vitejs/plugin-react; proxy /api
├── vitest.config.ts
├── tsconfig.json
├── tsconfig.app.json      # strict, ES2022, jsx=react-jsx
├── tsconfig.node.json
├── eslint.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx            # AppShell + RouterProvider
│   ├── index.css          # imports pdomain-ui tokens.css / primitives.css
│   ├── routes.tsx         # canonical route table (testable)
│   ├── api/
│   │   ├── client.ts
│   │   ├── types.ts       # AUTO-GENERATED from openapi.json
│   │   ├── runs.ts        # typed wrapper over runs endpoints
│   │   ├── jobs.ts        # SSE hookup
│   │   └── *.test.ts
│   ├── stores/
│   │   ├── ui-prefs.ts        # selectedProfile, kanban filters, log auto-scroll (zustand-persist)
│   │   ├── kanban-staging.ts  # pending split assignment until Apply (D-T23)
│   │   ├── selection.ts       # ephemeral kanban multi-select set
│   │   └── *.test.ts
│   ├── hooks/
│   │   ├── useProfiles.ts
│   │   ├── useKanban.ts
│   │   ├── useRun.ts
│   │   ├── useRunLog.ts
│   │   └── *.test.tsx
│   ├── pages/
│   │   ├── ProfilesPage.tsx       # list + create + edit profiles
│   │   ├── ProfileDetailPage.tsx  # one profile; nested: datasets / train / runs
│   │   ├── DatasetsPage.tsx       # dual kanban (detection + recognition)
│   │   ├── TrainPage.tsx          # detection + recognition config cards + Start
│   │   ├── RunsPage.tsx           # run history list
│   │   ├── RunDetailPage.tsx      # one run: live log + progress + artefacts + export
│   │   └── *.test.tsx
│   ├── components/
│   │   ├── ProfileEditDialog.tsx  # pdomain-ui Dialog + Field/FieldRow
│   │   ├── DetectionConfigCard.tsx
│   │   ├── RecognitionConfigCard.tsx
│   │   ├── RunControls.tsx        # Start / Stop buttons
│   │   ├── LossChart.tsx          # SPA-local; recharts
│   │   ├── ModelExportPanel.tsx   # SPA-local; model name + export
│   │   └── *.test.tsx
│   ├── lib/
│   │   ├── format.ts              # bytes, durations, percentages
│   │   ├── runConfig.ts           # task → config-schema map
│   │   ├── modelName.ts           # parse/format pd-<lang>-<typeface>-<task>-<date>
│   │   └── *.test.ts
│   └── test/
│       ├── setup.ts               # msw + jsdom
│       ├── server.ts              # msw handlers
│       └── factories.ts           # makeProfile / makeRun / makeKanbanView fixtures
└── public/
    └── favicon.svg
```

<!-- markdownlint-enable MD013 -->

No `tailwind.config.ts`, no `components.json`, no `src/components/ui/`,
no `src/styles/tokens.css` — pdomain-ui owns all of that.

---

## 3. Routing

React Router v7 data router. `routes.tsx` exports the route definitions
so tests can assert structure.

> Note: this route table (`routes.tsx` / `RunsPage.tsx` / `TrainPage.tsx`)
> predates and diverges from the shipped `frontend/src/App.tsx` routing —
> the shipped app uses `<Routes>`/`<Route>` in `App.tsx`, has no
> `/settings` route, and names pages differently (e.g. `RunListPage`,
> `NewRunPage`). Full reconciliation of this section with the shipped
> frontend is out of scope here; tracked as follow-up drift.

```ts
export const routes = [
  { path: "/", element: <Navigate to="/profiles" replace /> },
  { path: "/profiles", element: <ProfilesPage /> },
  { path: "/profiles/:profile", element: <ProfileDetailPage />, children: [
    { index: true, element: <Navigate to="datasets" replace /> },
    { path: "datasets", element: <DatasetsPage /> },
    { path: "train", element: <TrainPage /> },
    { path: "runs", element: <RunsPage /> },
  ]},
  { path: "/runs", element: <RunsPage /> },
  { path: "/runs/:run_id", element: <RunDetailPage /> },
];
```

URL invariants under [`13-driver-contract.md`](13-driver-contract.md):

- `/runs/{run_id}` is **stable** — log links, training-finished toasts,
  and model-export back-references all point here.
- `/profiles/{profile}/datasets` and `.../train` mirror the backend
  resource shape; deep-linkable.

Deferred routes — `/models`, `/eval`, `/publish` — are **not** in the
core-parity route table; they arrive with the deferred-milestone specs
(retirement plan Task 13).

---

## 4. State stores

### 4.1 Server state (`@tanstack/react-query`)

One query key per resource:

```ts
queryKey: ["profiles"]
queryKey: ["profile", name]
queryKey: ["kanban", profile]            // dual-task kanban view
queryKey: ["runs", { status?, profile?, task?, page }]
queryKey: ["run", run_id]
queryKey: ["public-settings"]
queryKey: ["vocabs"]                     // long stale time
```

Mutation success → **explicit** `invalidateQueries` for affected keys.
No refetch-on-window-focus (would interrupt running jobs in heavy-CPU
contexts).

### 4.2 UI prefs (`zustand` + `persist`)

```ts
interface UIPrefsStore {
  selectedProfile: string | null;
  setSelectedProfile: (name: string | null) => void;
  kanbanFilters: { showOnlyMissing: boolean; styleTagFilter: string | null };
  setKanbanFilters: (f: Partial<UIPrefsStore["kanbanFilters"]>) => void;
  logViewer: { autoScroll: boolean; wrap: boolean };
  setLogViewer: (s: Partial<UIPrefsStore["logViewer"]>) => void;
}
```

Persist key: `pdomain-ocr-trainer-spa.ui-prefs.v1`.

### 4.3 Kanban staging (`zustand`, **not** persisted) — D-T23

Holds the pending split assignment while the user drags. Cleared on
Apply (commit) or Discard (reset to server state) and on profile change.

```ts
interface KanbanStagingStore {
  staged: Record<string /* page_key */, "train" | "val" | "unassigned">;
  isDirty: boolean;                       // any divergence from server state
  move(pageKeys: string[], to: "train" | "val" | "unassigned"): void;
  reset(): void;                          // Discard
  diff(serverState): KanbanDiff;          // pending changes for the UI
}
```

### 4.4 Ephemeral selection (`zustand`, not persisted)

Kanban multi-select set; cleared on profile change.

```ts
interface SelectionStore {
  selectedKeys: Set<string>;
  anchorKey: string | null;               // for shift-range
  toggle(key: string): void;
  add(keys: string[]): void;
  clear(): void;
  setAnchor(key: string | null): void;
}
```

---

## 5. Generated API client

`make openapi-export` (see [`02-backend.md`](02-backend.md)) writes
`frontend/openapi.json` and runs `openapi-typescript` →
`frontend/src/api/types.ts`. CI gates on `git diff --exit-code`.

Hand-written wrappers under `src/api/*.ts` use the generated types:

<!-- markdownlint-disable MD013 -->

```ts
// api/runs.ts
import type { paths } from "./types";
type CreateRunRequest = paths["/api/runs"]["post"]["requestBody"]["content"]["application/json"];
type CreateRunResponse = paths["/api/runs"]["post"]["responses"]["202"]["content"]["application/json"];

export async function createRun(req: CreateRunRequest): Promise<CreateRunResponse> {
  return fetchJson("/api/runs", { method: "POST", body: req });
}
```

<!-- markdownlint-enable MD013 -->

`api/jobs.ts` is a thin layer over the pdomain-ui `useLongJob` hook, which
owns the SSE/polling subscription to a job's event stream
([D-T10](17-decisions.md), [D-T20](17-decisions.md)).

---

## 6. App chrome and component mapping

### 6.1 App chrome

The app is wrapped in the pdomain-ui `AppShell`:

<!-- markdownlint-disable MD013 -->

```text
┌────────────────────────────────────────────────────────────────────┐
│ AppShell · header  (TopNav + Breadcrumb)                           │
│  pdomain-ocr-training  [profile: clogaelach ▼]   [⊞ launcher]  v0.x      │
├──────────┬─────────────────────────────────────────────────────────┤
│ rail     │ main: <Outlet />                                        │
│ Profiles │                                                         │
│ Datasets │                                                         │
│ Train    │                                                         │
│ Runs     │                                                         │
│ Settings │                                                         │
└──────────┴─────────────────────────────────────────────────────────┘
```

<!-- markdownlint-enable MD013 -->

- `AppShell` props: `appId="pdomain-ocr-trainer-spa"`, `appDisplayName`,
  `appIconUrl`, `launcherSlot="header"`, `deployMode="local"`,
  `uiPrefsConfig`.
- The active-profile `Select` lives in the `TopNav`. Switching it
  updates `UIPrefsStore.selectedProfile` and, when on a profile-scoped
  route, navigates to `/profiles/{name}/datasets`.
- Cross-app launching uses `useSuiteSiblings`; active suite jobs surface
  via the pdomain-ui `JobsDrawer` / `useSuiteJobs`.

### 6.2 Legacy element → component mapping

<!-- markdownlint-disable MD013 -->

| Legacy NiceGUI element | Component |
| --- | --- |
| App header/banner | pdomain-ui `AppShell` + `TopNav` + `LauncherSlot` (`useSuiteSiblings`) |
| Profile card (active-profile picker) | pdomain-ui `Select` in `TopNav`; `ProfilesPage` uses `Card` + `Field`/`FieldRow` |
| Profile edit (language / typeface / display_name) | `ProfileEditDialog` — pdomain-ui `Dialog` + `Field`/`FieldRow` + `Select` |
| Detection config card | `DetectionConfigCard` — pdomain-ui `Card` + `Accordion` (help) + `Field`/`FieldRow` + `Input`/`Select` + `Button` |
| Recognition config card | `RecognitionConfigCard` — same; `vocab` is a `Field` with `Select` + a `CUSTOM:` text `Input` |
| Start / Stop training buttons | `RunControls` — pdomain-ui `Button` (`run-start-button` testid) |
| Training run / progress | pdomain-ui `Progress` + `JobStatusPip` + `useLongJob` (SSE) |
| Live training-output log | pdomain-ui **`LogViewer`** |
| Dataset kanban (drag-drop) | pdomain-ui **`KanbanBoard` / `KanbanColumn` / `PageChip`** |
| Model name / export controls | **SPA-local `ModelExportPanel`** in `RunDetailPage` |
| Loss curve | **SPA-local `LossChart`** (recharts) |

<!-- markdownlint-enable MD013 -->

### 6.3 New pdomain-ui components (specced here, built in pdomain-ui)

- **`KanbanBoard` / `KanbanColumn` / `PageChip`** — pdomain-ui owns the
  `dnd-kit` integration (PointerSensor for mouse, KeyboardSensor for
  a11y) and per-column virtualization. The trainer supplies render-props
  for chip content and column headers, plus the data. Move events are
  routed into the SPA's `kanban-staging` store; the board renders the
  staged arrangement and a pending-diff affordance; "Apply" / "Discard"
  are SPA-owned actions ([D-T23](17-decisions.md)).
- **`LogViewer`** — pdomain-ui owns virtualization (`@tanstack/react-virtual`)
  and the auto-scroll / wrap toggles. Fed a stream of lines; the trainer
  wires it to `useLongJob` events. Client buffer cap configurable; the
  full log stays on disk for the run-detail tail endpoint.
- **`Field` / `FieldRow`** — labelled form-row primitive: a label, a
  control slot, an optional help/`Accordion` slot, and an error slot
  driven by `422 ErrorEnvelope` `details[].loc`.
- **`JobStatusPip`** — a job-state pip (queued / running / succeeded /
  failed / cancelled — `JobState` per pdomain-ocr-ops; render "Done" via the
  `label` prop when UX calls for it), a job-aware variant of pdomain-ui
  `StatusPip`.

The trainer's `DatasetsPage` shows **two `KanbanBoard`s** — one for the
detection dataset, one for recognition — per the design's "dual kanban".

### 6.4 SPA-local components

- **`LossChart`** — `recharts` line chart over a run's `progress.jsonl`;
  downsamples to ~500 points for long runs. App-specific; not a pdomain-ui
  candidate ([D-T14](17-decisions.md)).
- **`ModelExportPanel`** — model-name (`pd-<lang>-<typeface>-<task>-<date>`,
  [D-T6](17-decisions.md)) + export-to-`dist/` controls, shown on
  `RunDetailPage`. App-specific composition.

---

## 7. Page-level conventions

- Pages render inside the `AppShell` `main` slot; each page sets its
  `TopNav` breadcrumb + an action slot.
- Long-running actions never block the route: starting training kicks
  off a run and bounces the user to `/runs/{run_id}` with a "running"
  toast.
- Empty states have one illustration + an explicit CTA button. No
  silent empty tables.
- Form submission uses `react-query` mutations; on `422 ErrorEnvelope`
  the form maps `details[].loc` to per-`FieldRow` errors
  ([`02-backend.md`](02-backend.md)).

---

## 8. Performance constraints

- `KanbanBoard` columns can render thousands of page chips — pdomain-ui
  virtualizes per column.
- `LogViewer` virtualizes lines and formats only visible ones; client
  buffer cap (~50k lines); the server retains the full log on disk.
- `LossChart` downsamples to ~500 points; full data via the JSONL
  endpoint.

---

## 9. `data-testid` contract

The driver-facing surface is part of the contract from M0
([`13-driver-contract.md`](13-driver-contract.md),
[D-T12](17-decisions.md)). Because the kanban and log live in pdomain-ui,
these IDs are a **shared expectation between pdomain-ui and trainer-spa** —
pdomain-ui's `KanbanColumn` / `LogViewer` accept a `data-testid` prop the
trainer sets.

Minimum contract:

<!-- markdownlint-disable MD013 -->

| `data-testid` | Element |
| --- | --- |
| `profile-selector` | active-profile `Select` in `TopNav` |
| `config-submit` | detection + recognition config-card submit `Button`s (scoped per card) |
| `kanban-detection-column` | detection `KanbanColumn` |
| `kanban-recognition-column` | recognition `KanbanColumn` |
| `training-log-panel` | `LogViewer` root |
| `run-start-button` | `RunControls` Start `Button` |

<!-- markdownlint-enable MD013 -->

---

## 10. Testing posture

- **Vitest + @testing-library/react** — unit tests per hook + component.
  `msw` mocks at the network boundary; never mock react-query directly.
- **Playwright** (Chromium) for top-of-funnel flows: create profile →
  stage + Apply kanban moves → start a stubbed training run → see the
  log panel populate → see the run reach a terminal state. Detail in
  [`14-testing.md`](14-testing.md).

---

## 11. Citations

- App-shell + routing convention: shipped `pdomain-ocr-labeler-spa` and
  `pdomain-ocr-simple-gui` frontends.
- pdomain-ui component surface: workspace cross-cut design
  (`ocr-container/docs/specs/2026-05-16-cross-cut-design.md` §4, §6).
- Legacy trainer UI surface: `pdomain-ocr-training/src/pdomain_ocr_training/ui.py`
  - `dataset_ui.py` (profile card, detection card, recognition card,
  output card, dataset section).
