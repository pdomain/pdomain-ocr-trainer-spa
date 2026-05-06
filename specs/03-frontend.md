# 03 — Frontend (React/Vite/TS)

The SPA half of `pd-ocr-trainer-spa`. Built with Vite, served from
the FastAPI wheel in production, served via Vite dev-server with
proxy in development.

This spec covers the **shell**: routing, state stores, generated API
client, app chrome, and the page tree. Per-feature specs deepen each
piece.

> Required reading: [`00-overview.md`](00-overview.md), [`02-backend.md`](02-backend.md).

---

## 1. Project layout

```
frontend/
├── package.json
├── package-lock.json
├── index.html             # loads /env.js then /src/main.tsx
├── vite.config.ts         # @vitejs/plugin-react; proxy /api
├── vitest.config.ts
├── tsconfig.json
├── tsconfig.app.json      # strict, ES2022, jsx=react-jsx
├── tsconfig.node.json
├── tailwind.config.ts
├── postcss.config.js
├── eslint.config.ts
├── components.json        # shadcn/ui config
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css
│   ├── routes.ts          # canonical route table (testable)
│   ├── api/
│   │   ├── client.ts
│   │   ├── types.ts       # AUTO-GENERATED from openapi.json
│   │   ├── runs.ts        # typed wrapper over runs endpoints
│   │   ├── jobs.ts        # SSE hookup
│   │   └── *.test.ts
│   ├── stores/
│   │   ├── ui-prefs.ts    # selectedProfile, kanban filters, log auto-scroll, splitter (zustand-persist)
│   │   ├── selection.ts   # ephemeral kanban selection set
│   │   └── *.test.ts
│   ├── hooks/
│   │   ├── useProfiles.ts
│   │   ├── useKanban.ts
│   │   ├── useRun.ts
│   │   ├── useRunLog.ts
│   │   ├── useJobProgress.ts
│   │   ├── useNotificationStream.ts
│   │   ├── useHotkey.ts
│   │   └── *.test.tsx
│   ├── pages/
│   │   ├── ProfilesPage.tsx           # list + create + edit profiles
│   │   ├── ProfileDetailPage.tsx      # single profile, tabs: Datasets / Runs / Models
│   │   ├── DatasetsPage.tsx           # kanban for one (profile, task)
│   │   ├── RunsPage.tsx               # run list (all profiles)
│   │   ├── RunDetailPage.tsx          # one run: log + progress + artefacts
│   │   ├── ModelsPage.tsx             # model registry
│   │   ├── ModelDetailPage.tsx        # one model: sidecar + publish
│   │   ├── EvalPage.tsx               # configure + launch eval
│   │   ├── EvalResultPage.tsx         # CER/WER + glyph slicing
│   │   ├── PublishPage.tsx            # HF publish (gated)
│   │   ├── SettingsPage.tsx           # read-only config view
│   │   └── *.test.tsx
│   ├── components/
│   │   ├── HeaderBar.tsx              # version, profile selector, jobs badge
│   │   ├── SidebarNav.tsx             # left nav: Profiles / Datasets / Runs / Models / Eval / Publish
│   │   ├── ProfileSelector.tsx
│   │   ├── ProfileEditDialog.tsx      # language + typeface + display_name
│   │   ├── KanbanBoard.tsx            # see 05-dataset-kanban.md
│   │   ├── KanbanColumn.tsx
│   │   ├── KanbanCard.tsx             # project-row OR page-chip variant
│   │   ├── PageChip.tsx
│   │   ├── RunForm.tsx                # task-aware form (detection|recognition|typeface|glyph)
│   │   ├── RunArgsEditor.tsx          # vocab, epochs, batch, augment toggles
│   │   ├── RunStatusBadge.tsx
│   │   ├── RunProgressBar.tsx
│   │   ├── LogViewer.tsx              # virtualized; auto-scroll toggle (see 06)
│   │   ├── LossChart.tsx              # recharts; consumes progress.jsonl
│   │   ├── ModelCard.tsx
│   │   ├── ModelSidecarView.tsx
│   │   ├── EvalMetricsTable.tsx       # CER/WER overall + glyph-feature slices
│   │   ├── PublishDialog.tsx
│   │   ├── BusyOverlay.tsx
│   │   ├── JobsBadge.tsx              # header badge: live job count
│   │   ├── NotificationToaster.tsx    # sonner wrapper
│   │   └── ui/                        # shadcn primitives
│   ├── lib/
│   │   ├── format.ts                  # bytes, durations, percentages
│   │   ├── runArgs.ts                 # task → arg-schema map
│   │   ├── progressParse.ts           # "epoch X/Y loss=Z" → JobProgress
│   │   ├── modelName.ts               # parse + format pd-<lang>-<typeface>-<task>-<date>
│   │   └── *.test.ts
│   ├── styles/
│   │   └── tokens.css
│   └── test/
│       ├── setup.ts                   # msw + jsdom
│       ├── server.ts                  # msw handlers
│       └── factories.ts               # makeProfile / makeRun / makeKanbanView fixtures
└── public/
    └── favicon.svg
```

---

## 2. Routing

Single-route-tree; React Router v7 data routers. `routes.ts` exports
the route definitions so tests can assert structure.

```ts
export const routes = [
  { path: "/", element: <Navigate to="/profiles" replace /> },
  { path: "/profiles", element: <ProfilesPage /> },
  { path: "/profiles/:profile", element: <ProfileDetailPage />, children: [
    { index: true, element: <Navigate to="datasets/recognition" replace /> },
    { path: "datasets/:task", element: <DatasetsPage /> },
    { path: "runs", element: <RunsPage /> },
    { path: "models", element: <ModelsPage /> },
  ]},
  { path: "/runs", element: <RunsPage /> },
  { path: "/runs/:run_id", element: <RunDetailPage /> },
  { path: "/models", element: <ModelsPage /> },
  { path: "/models/:name", element: <ModelDetailPage /> },
  { path: "/eval", element: <EvalPage /> },
  { path: "/eval/:run_id/result", element: <EvalResultPage /> },
  { path: "/publish", element: <PublishPage /> },
  { path: "/settings", element: <SettingsPage /> },
];
```

URL invariants under [`13-driver-contract.md`](13-driver-contract.md):

- `/runs/{run_id}` is **stable** — log links, training-finished
  toasts, model sidecar back-references all point here.
- `/profiles/{profile}/datasets/{task}` mirrors the backend resource
  shape; deep-linkable.

---

## 3. State stores

### 3.1 Server state (`@tanstack/react-query`)

One query key per resource:

```ts
queryKey: ["profiles"]
queryKey: ["profile", name]
queryKey: ["kanban", profile, task]
queryKey: ["runs", { status?, profile?, task?, page }]
queryKey: ["run", run_id]
queryKey: ["models", { profile?, task? }]
queryKey: ["model", name]
queryKey: ["eval-result", run_id]
queryKey: ["sources"]
queryKey: ["public-settings"]
queryKey: ["vocabs"]                      // long stale time; matches backend cache
```

Mutation success → **explicit** `invalidateQueries` for affected
keys. No global refetch-on-window-focus (would interrupt running
jobs in heavy-CPU contexts).

### 3.2 UI state (`zustand` + `persist`)

```ts
interface UIPrefsStore {
  selectedProfile: string;                // last-selected; null on first load
  setSelectedProfile: (name: string) => void;

  kanbanFilters: { showOnlyMissing: boolean; styleTagFilter: string | null };
  setKanbanFilters: (f: Partial<UIPrefsStore["kanbanFilters"]>) => void;

  logViewer: { autoScroll: boolean; wrap: boolean };
  setLogViewer: (s: Partial<UIPrefsStore["logViewer"]>) => void;

  splitter: { leftPx: number };
  setSplitter: (s: Partial<UIPrefsStore["splitter"]>) => void;
}
```

Persist key: `pd-ocr-trainer-spa.ui-prefs.v1`.

### 3.3 Ephemeral selection (`zustand`, **not** persisted)

Kanban multi-select set; cleared on profile change.

```ts
interface SelectionStore {
  selectedKeys: Set<string>;              // "<split>:<project>:<page_or_crop>"
  anchorKey: string | null;               // for shift-range
  toggle(key: string): void;
  add(keys: string[]): void;
  clear(): void;
  setAnchor(key: string | null): void;
}
```

---

## 4. Generated API client

`make openapi-export` (see [`02-backend.md`](02-backend.md) §7) writes
`frontend/openapi.json` and runs `openapi-typescript` →
`frontend/src/api/types.ts`. CI gates on `git diff --exit-code`.

Hand-written wrappers under `src/api/*.ts` use the generated types:

```ts
// api/runs.ts
import type { paths } from "./types";
type CreateRunRequest = paths["/api/runs"]["post"]["requestBody"]["content"]["application/json"];
type CreateRunResponse = paths["/api/runs"]["post"]["responses"]["202"]["content"]["application/json"];

export async function createRun(req: CreateRunRequest): Promise<CreateRunResponse> {
  return fetchJson("/api/runs", { method: "POST", body: req });
}
```

`api/jobs.ts` exposes a `subscribeToJob(jobId, on_event)` helper that
wraps `EventSource` and yields typed `JobEvent` objects.

---

## 5. App chrome

```
┌────────────────────────────────────────────────────────────────────┐
│ HeaderBar                                                          │
│ ┌──────┐ pd-ocr-trainer  [profile: clogaelach▼]  [jobs: 1●]  v0.x │
│ │ logo │                                                           │
│ └──────┘                                                           │
├──────────┬─────────────────────────────────────────────────────────┤
│ Sidebar  │ <Outlet />                                              │
│ Profiles │                                                         │
│ Datasets │                                                         │
│ Runs     │                                                         │
│ Models   │                                                         │
│ Eval     │                                                         │
│ Publish  │                                                         │
│ Settings │                                                         │
└──────────┴─────────────────────────────────────────────────────────┘
```

`HeaderBar` always shows the active profile picker; switching
updates `UIPrefsStore.selectedProfile` and navigates to
`/profiles/{name}/datasets/recognition` if the user is on a
profile-scoped sub-route.

`JobsBadge` reads `["jobs", "active-count"]` (a thin GET that returns
`{count: int}`) every 5 s when any job is known to be running, off
otherwise.

---

## 6. Page-level conventions

- All pages use a single `<PageShell title="..." actions={...}>`
  wrapper (header bar + breadcrumb + action slot).
- Long-running actions never block the route; they kick off a `Run`
  and the user is bounced to `/runs/{run_id}` with a "running" toast.
- Empty states have a single illustration + an explicit
  call-to-action (CTA) button. No silent empty tables.
- Form submission uses `react-query` mutations; on
  `422 ErrorEnvelope` the form maps `details[].loc` to per-field
  errors. ([`02-backend.md`](02-backend.md) §6.)

---

## 7. Performance constraints

- The kanban page can render thousands of page chips. Use
  `@tanstack/react-virtual` per column.
- `LogViewer` virtualizes lines and only formats visible ones. Buffer
  cap = 50k lines on the client; older lines are GC'd (server retains
  full log on disk for the run-detail tail endpoint).
- `LossChart` (recharts) downsamples to ~500 points if the run has
  more progress events. Full data stays available via the JSONL endpoint.

---

## 8. Testing posture

- **Vitest + @testing-library/react.** Unit tests per hook +
  component. msw mocks at the network boundary; never mock react-query
  directly.
- **Playwright** for top-of-funnel flows: create profile → drag pages
  in kanban → start training (with a `local_subprocess` runner that
  invokes `sleep 1`) → see run terminal → see model in registry.
  Detail in [`14-testing.md`](14-testing.md).

---

## 9. Citations

- Routing convention: `pd-ocr-labeler-spa/specs/03-frontend.md`.
- Stores convention: `pd-ocr-labeler-spa/specs/03-frontend.md` §3.
- pgdp-prep base: `pd-prep-for-pgdp/frontend/`.
- Legacy trainer page surface: `pd-ocr-trainer/src/pd_ocr_trainer/ui.py`
  + `dataset_ui.py`.
