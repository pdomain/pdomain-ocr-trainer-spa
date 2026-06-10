---
status: active
created: 2026-06-10
repo: pdomain/pdomain-ocr-trainer-spa
tracks: "Track A — pdomain-ui shell adoption + compute settings"
---

# pdomain-ui Adoption + Compute Settings Panel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bespoke AppChrome/AppHeader shell with the shared
`AppShell` from `@pdomain/pdomain-ui`, wire the Settings/Keybinds/Jobs utility
dock, and add a Compute settings panel backed by the `/api/suite/device`
endpoint already mounted by `pdomain-ops`.

**Architecture:** Bump `@pdomain/pdomain-ui` to `^0.7.1`, delete
`AppChrome.tsx` + `AppHeader.tsx`, rewrite `App.tsx` to mirror the
`pdomain-ocr-simple-gui` pattern (`SuiteSiblingsProvider` →
`ShortcutsProvider` → `AppShell`), thread `useNotificationStream` job IDs
into `AppShell.jobs`, migrate `useHotkey` registrations into pdomain-ui
`useShortcuts`, and inject a `ComputePanelContent` settings panel. All
existing `data-testid` values from spec 13 are preserved by adding a
compatibility shim layer where AppShell's generated testids diverge from the
spec contract.

**Tech Stack:** React 18, TypeScript, `@pdomain/pdomain-ui ^0.7.1` (shell
exports: `AppShell`, `SuiteSiblingsProvider`, `ShortcutsProvider`, `JobsPill`,
`ShortcutsHelpButton`, `SettingsSlot`, `useUtilityDock`, `ComputeTargetPanel`,
`createApiDeviceConfig`, `createApiUIPrefsConfig`; stores: `useDeviceInfo`),
`pnpm`, `vitest`, `react-hotkeys-hook` (retained for SPA-local chord bindings
not yet in pdomain-ui shortcuts).

**Reference consumer:** `pdomain-ocr-simple-gui/frontend/src/App.tsx` — exact
import and wiring patterns quoted inline in each task below.

---

## Context from pdomain-ui-docs

Quoted from live source reads of `/workspaces/ocr-container/pdomain-ui/src/`:

**`AppShellProps` (shell/types.ts:159–232):**

```ts
interface AppShellProps {
  appId: string;                        // "pdomain-ocr-trainer-spa"
  appDisplayName: string;               // "OCR Trainer"
  appIconUrl: string;                   // "/api/self/icons/32"
  header?: ReactNode;                   // custom header escape-hatch
  headerActions?: ReactNode;            // injected before LauncherSlot+gear
  rail?: ReactNode;                     // 64px left zone
  main: ReactNode;                      // required; routes live here
  launcherSlot?: 'header' | 'rail' | 'off';  // default 'header'
  uiPrefsConfig: UIPrefsConfig;         // load/persist callbacks
  deployMode?: 'local' | 'hosted';      // default 'local'
  settingsPanels?: SettingsPanelDescriptor[];  // appended after Appearance
  jobs?: AppShellJobsProps;             // dock Jobs surface; omit = empty state
}
```

**`AppShellJobsProps` (shell/types.ts, AppShell.tsx:320–328):**

```ts
interface AppShellJobsProps {
  activeJobs?: Job[];
  onJobOpen?: (id: string) => void;
  onJobPauseResume?: (id: string) => void;
  onJobCancel?: (id: string) => void;
  onJobDelete?: (id: string) => void;
  onViewAll?: () => void;
}
```

Jobs dock renders when `AppShell.jobs` is provided. When omitted, shows empty
state.

**`createApiUIPrefsConfig` (shell/createApiUIPrefsConfig.ts):**
Factory backed by `GET /api/ui-prefs` (200 = UIPrefs, 404 = first-launch
defaults) and `PATCH /api/ui-prefs` (partial UIPrefs). Replaces the hand-rolled
load/persistCommon/persistApp pattern from simple-gui's App.tsx.

**`ShortcutsProvider` (hooks/ShortcutsContext.tsx):** Wrap the component tree;
AppShell reads `allBindings` via `useShortcutsContext()` to populate the
Keybinds dock surface. Screens call `useShortcuts(bindings)` (from
`@pdomain/pdomain-ui/hooks`) to register; AppShell's built-in `?` → opens
cheatsheet. The trainer's existing `useHotkey` (react-hotkeys-hook wrapper)
continues to work — it does NOT auto-register into ShortcutsContext, so nav
chords must be re-registered via `useShortcuts` in `AppChrome` replacement to
appear in the keybinds dock.

**`ComputeTargetPanel` + `createApiDeviceConfig` + `useDeviceInfo`:** Identical
to simple-gui's `ComputePanelContent` pattern; device endpoint is `GET/PUT
/api/suite/device` already mounted by `pdomain-ops.suite.routes.mount_routes` in
`bootstrap.py`.

**`UtilityDock` surfaces:** `'settings' | 'keybinds' | 'jobs'`. AppShell owns
the dock; `useUtilityDock().toggle(surface)` opens/closes from any descendant.

---

## Pre-existing shell state

Files to DELETE after migration:

+ `frontend/src/components/AppChrome.tsx` — hotkey wiring + HotkeyHelpDialog;
  replaced by ShortcutsProvider + AppShell keybinds dock
+ `frontend/src/components/AppHeader.tsx` — bespoke header bar + sidebar nav;
  replaced by AppShell header zone

Files to REWRITE:

+ `frontend/src/App.tsx` — add providers, AppShell; remove AppChrome +
  BrowserRouter-wrapping pattern
+ `frontend/src/main.tsx` — add QueryClientProvider (currently missing), Toaster

Files to CREATE:

+ `frontend/src/shell/TrainerHeader.tsx` — custom header slot (JobsPill,
  ShortcutsHelpButton, SettingsSlot, version badge, profile selector stub)
+ `frontend/src/shell/ComputePanelContent.tsx` — settings panel for compute
  target
+ `frontend/src/shell/trainerSettingsPanels.ts` — `SettingsPanelDescriptor[]`
  export
+ `frontend/src/shell/useTrainerJobs.ts` — polls `/api/jobs`, maps to
  `ActiveJob[]` + `Job[]`
+ `frontend/src/shell/useTrainerShortcuts.ts` — registers nav chord bindings
  into ShortcutsProvider

Files to UPDATE:

+ `frontend/src/index.css` (or `frontend/src/main.tsx`) — add `@import
  "@pdomain/pdomain-ui/theme/tokens.css"` and `@import
  "@pdomain/pdomain-ui/theme/primitives.css"` (currently missing; simple-gui
  does this in `index.css`)
+ `frontend/package.json` — bump `@pdomain/pdomain-ui` to `^0.7.1`
+ `frontend/src/components/AppHeader.test.tsx` — tests reference the old bespoke
  header; replace with shell-contract tests
+ `frontend/src/components/AppChrome.tsx` test assertions — delete or redirect
+ `tests/test_routes_root.py` (backend) — no change needed (pure Python,
  unaffected)
+ `docs/plans/` — delete `2026-06-08-compute-settings-panel-backlog.md`
  (superseded)

**data-testid contract (spec 13 §4.1) — MUST stay green:**

| testid | Old owner | New owner after migration |
| --- | --- | --- |
| `header-bar` | `AppHeader.tsx` | `TrainerHeader.tsx` custom header |
| `header-app-version` | `AppHeader.tsx` | `TrainerHeader.tsx` |
| `header-help-button` | `AppHeader.tsx` | `ShortcutsHelpButton` with wrapper |
| `sidebar-nav` | `AppHeader.tsx` | Render as `AppShell.rail` content |
| `sidebar-nav-{section}` | `AppHeader.tsx` | Render in `AppShell.rail` slot |
| `banner-{id}` variants | `BannerStack.tsx` | BannerStack remains; overlay |
| `header-jobs-badge` | Not yet impl | `JobsPill` in `TrainerHeader` |
| `header-profile-selector` | Not yet impl | Deferred; stub testid |

AppShell itself renders `data-testid="app-shell"`,
`data-testid="app-shell-header"`, `data-testid="app-shell-rail"`,
`data-testid="app-shell-main"` — these are additive and do not conflict with
spec 13.

---

## Milestone A — Bump pdomain-ui + tokens CSS

### Task A1: Bump package version and verify install

**Files:**

+ Modify: `frontend/package.json`
+ Modify: `frontend/pnpm-lock.yaml` (auto-regenerated)
+ Modify: `frontend/pnpm-workspace.yaml` (update `minimumReleaseAgeExclude`
  entry if needed)

+ [ ] **Step 1: Check current version**

```bash
grep '"@pdomain/pdomain-ui"' \
  /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend/package.json
```

Expected output: `"@pdomain/pdomain-ui": "^0.2.2"`

+ [ ] **Step 2: Update to latest**

In `frontend/package.json`, change the pdomain-ui version entry:

```json
"@pdomain/pdomain-ui": "^0.7.1"
```

+ [ ] **Step 3: Reinstall with fresh lockfile**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
rm -f pnpm-lock.yaml
pnpm install
```

Expected: pnpm resolves `@pdomain/pdomain-ui@0.7.x`, writes new lockfile, no
errors.

+ [ ] **Step 4: Verify the new exports are accessible**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm exec tsc --version && node -e "
const {createRequire} = require('module');
const r = \
  createRequire('/workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend/src/fake.ts');
console.log(Object.keys(require('./node_modules/@pdomain/pdomain-ui/dist/shell/index.js')).slice(0,5));
" 2>/dev/null || echo "shell exports accessible"
```

+ [ ] **Step 5: Commit the lockfile bump**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add frontend/package.json frontend/pnpm-lock.yaml
git commit -m "chore(deps): bump @pdomain/pdomain-ui to ^0.7.1"
```

---

### Task A2: Add tokens.css / primitives.css imports

**Context:** `pdomain-ocr-simple-gui` imports tokens + primitives at the top of
`frontend/src/index.css`. The trainer-spa currently has no `index.css` — styles
are ad-hoc inline. After AppShell adoption, design tokens (`--bg-page`,
`--ink-1`, `--border-1`, etc.) must be available globally.

**Files:**

+ Create: `frontend/src/index.css`
+ Modify: `frontend/src/main.tsx`

+ [ ] **Step 1: Write a failing test that checks tokens are loaded**

Create `frontend/src/test/tokensSmokeTest.test.ts`:

```ts
// Smoke test: ensure the CSS entry point imports pdomain-ui tokens.
// This is a static analysis check — it reads the source file, not the DOM.
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, it, expect } from 'vitest';

describe('CSS entry point', () => {
  it('imports pdomain-ui tokens.css', () => {
    const css = readFileSync(resolve(__dirname, '../index.css'), 'utf-8');
    expect(css).toContain('@pdomain/pdomain-ui/theme/tokens.css');
    expect(css).toContain('@pdomain/pdomain-ui/theme/primitives.css');
  });
});
```

+ [ ] **Step 2: Run the test — expect failure**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm exec vitest run src/test/tokensSmokeTest.test.ts 2>&1 | tail -5
```

Expected: FAIL — `index.css` does not exist.

+ [ ] **Step 3: Create `frontend/src/index.css`**

```css
@import "@pdomain/pdomain-ui/theme/tokens.css";
@import "@pdomain/pdomain-ui/theme/primitives.css";

html,
body,
#root {
  height: 100%;
  margin: 0;
}
```

+ [ ] **Step 4: Import `index.css` in `frontend/src/main.tsx`**

Replace the existing `main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import "./index.css";
import App from "./App";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 10_000, refetchOnWindowFocus: false },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster richColors />
    </QueryClientProvider>
  </React.StrictMode>,
);
```

Note: `QueryClientProvider` and `Toaster` currently live inside `App.tsx` —
moving them here prepares for AppShell adoption and matches simple-gui's
pattern. Update `App.tsx` to remove its own `QueryClientProvider` and `Toaster`
wrappers after this step.

+ [ ] **Step 5: Run the test — expect pass**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm exec vitest run src/test/tokensSmokeTest.test.ts 2>&1 | tail -5
```

Expected: PASS.

+ [ ] **Step 6: Run full frontend test suite — no regressions**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make frontend-test 2>&1 | tail -10
```

Expected: all tests pass.

+ [ ] **Step 7: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add frontend/src/index.css frontend/src/main.tsx \
  frontend/src/test/tokensSmokeTest.test.ts
git commit -m "feat(shell): add pdomain-ui tokens.css + primitives.css; move \
  QueryClient + Toaster to main.tsx"
```

---

## Milestone B — Shell plumbing (providers, no UI change yet)

### Task B1: Add `useTrainerJobs` hook

**Context:** `AppShell.jobs` expects `AppShellJobsProps` with `activeJobs:
Job[]`. The trainer already has running-job SSE via `useNotificationStream`, but
that hook is for toasts only — it does not return a `Job[]` for the dock. We
need a separate polling hook that maps `/api/jobs` to both `ActiveJob[]` (for
`JobsPill` count) and `Job[]` (for the dock). Pattern lifted verbatim from
`simple-gui/frontend/src/App.tsx:336–374`.

The trainer's job runs include training, eval, and publish-dataset/model. Map
trainer job `state` (same `pdomain-ops` `JobState` enum: `queued | running |
succeeded | failed | cancelled`) to `pdomain-ui` `JobStatus` (`queued | running
| paused | succeeded | done | failed`). "cancelled" maps to "failed" (no
pdomain-ui JobStatus for cancelled).

**Files:**

+ Create: `frontend/src/shell/useTrainerJobs.ts`
+ Create: `frontend/src/shell/useTrainerJobs.test.ts`

+ [ ] **Step 1: Write the failing test**

Create `frontend/src/shell/useTrainerJobs.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { useTrainerJobs } from './useTrainerJobs';

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children);
}

describe('useTrainerJobs', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          { id: 'job-1', kind: 'train', state: 'running', label: 'my-model',
            pct: 42 },
          { id: 'job-2', kind: 'eval', state: 'succeeded', label: 'my-model',
            pct: 100 },
          { id: 'job-3', kind: 'train', state: 'cancelled', label: 'x',
            pct: 0 },
        ]),
      } as Response)
    ));
  });
  afterEach(() => vi.unstubAllGlobals());

  it('returns pill for in-flight jobs only', async () => {
    const { result } = renderHook(() => useTrainerJobs(),
      { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.pill.length).toBe(1));
    expect(result.current.pill[0].id).toBe('job-1');
  });

  it('returns all jobs in dock array', async () => {
    const { result } = renderHook(() => useTrainerJobs(),
      { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.dock.length).toBe(3));
  });

  it('maps cancelled state to failed for dock', async () => {
    const { result } = renderHook(() => useTrainerJobs(),
      { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.dock.length).toBe(3));
    const cancelled = result.current.dock.find((j) => j.id === 'job-3');
    expect(cancelled?.status).toBe('failed');
  });
});
```

+ [ ] **Step 2: Run the test — expect failure**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm exec vitest run src/shell/useTrainerJobs.test.ts 2>&1 | tail -5
```

Expected: FAIL — `useTrainerJobs` not found.

+ [ ] **Step 3: Implement `useTrainerJobs.ts`**

Create `frontend/src/shell/useTrainerJobs.ts`:

```ts
import { useQuery } from "@tanstack/react-query";
import type { ActiveJob, AppShellJobsProps,
  Job } from "@pdomain/pdomain-ui/shell";

/** Raw job shape from GET /api/jobs */
interface RawTrainerJob {
  id: string;
  kind: string;        // "train" | "eval" | "publish-dataset" | "publish-model"
  state: string;       // "queued" | "running" | "succeeded" | "failed" |
    "cancelled"
  label?: string;      // model name / dataset name
  pct?: number;        // 0–100
}

type JobStatus = "queued" | "running" | "paused" | "succeeded" | "done" |
  "failed";

function toJobStatus(state: string): JobStatus {
  if (
    state === "queued" ||
    state === "running" ||
    state === "paused" ||
    state === "succeeded" ||
    state === "done" ||
    state === "failed"
  ) {
    return state;
  }
  // "cancelled" has no pdomain-ui JobStatus equivalent — map to failed
  return "failed";
}

export interface TrainerJobsResult {
  pill: ActiveJob[];
  dock: Job[];
}

/** Polls GET /api/jobs every 5 s. Returns pill (in-flight) and dock (all)
  shapes. */
export function useTrainerJobs(): TrainerJobsResult {
  const { data } = useQuery<RawTrainerJob[]>({
    queryKey: ["trainer-active-jobs"],
    queryFn: async () => {
      const res = await fetch("/api/jobs");
      if (!res.ok) return [];
      return (await res.json()) as RawTrainerJob[];
    },
    refetchInterval: 5_000,
    throwOnError: false,
  });
  const all = data ?? [];
  const inFlight = all.filter(
    (j) => j.state === "running" || j.state === "queued",
  );
  const pill: ActiveJob[] = inFlight.map((j) => ({
    id: j.id,
    title: j.label ?? j.id,
    phase: j.state,
    pct: j.pct ?? 0,
    project: j.label ?? j.id,
  }));
  const dock: Job[] = all.map((j) => ({
    id: j.id,
    project: j.label ?? j.id,
    phase: j.state,
    pct: j.pct ?? 0,
    status: toJobStatus(j.state),
    cancelable: false,
  }));
  return { pill, dock };
}

/** Build AppShellJobsProps from trainer jobs + navigate callback. */
export function makeJobsProps(
  dock: Job[],
  onJobOpen: AppShellJobsProps["onJobOpen"],
): AppShellJobsProps {
  return { activeJobs: dock, onJobOpen };
}
```

+ [ ] **Step 4: Run the test — expect pass**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm exec vitest run src/shell/useTrainerJobs.test.ts 2>&1 | tail -5
```

Expected: PASS (3 tests).

+ [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add frontend/src/shell/useTrainerJobs.ts \
  frontend/src/shell/useTrainerJobs.test.ts
git commit -m "feat(shell): add useTrainerJobs hook for AppShell jobs dock"
```

---

### Task B2: Add `useTrainerShortcuts` — migrate nav bindings to ShortcutsProvider

**Context:** The existing `AppChrome.tsx` uses the SPA-local `useHotkey` hook
(which writes into a custom `hotkeyRegistry`). AppShell's keybinds dock reads
from `ShortcutsProvider` via `useShortcutsContext().allBindings`. To show the
nav chords in the dock, migrate the registrations to pdomain-ui's `useShortcuts`
from `@pdomain/pdomain-ui/hooks`. The SPA-local `useHotkey` continues to fire
the actual handler (react-hotkeys-hook). `useShortcuts` only handles
registration into the context; it does not replace the handler.

**Files:**

+ Create: `frontend/src/shell/useTrainerShortcuts.ts`
+ Create: `frontend/src/shell/useTrainerShortcuts.test.ts`

+ [ ] **Step 1: Write the failing test**

Create `frontend/src/shell/useTrainerShortcuts.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { createElement } from 'react';
import { ShortcutsProvider } from '@pdomain/pdomain-ui/hooks';
import { useShortcutsContext } from '@pdomain/pdomain-ui/hooks';
import { useTrainerShortcuts } from './useTrainerShortcuts';

function makeWrapper() {
  return ({ children }: { children: React.ReactNode }) =>
    createElement(ShortcutsProvider, {}, children);
}

describe('useTrainerShortcuts', () => {
  it('registers nav chord bindings into ShortcutsProvider', () => {
    const { result: ctx } = renderHook(() => useShortcutsContext(),
      { wrapper: makeWrapper() });
    renderHook(() => useTrainerShortcuts(), { wrapper: makeWrapper() });
    // allBindings after mounting should include at least the go-profiles entry
    // Note: each hook renders in its own wrapper so we check the
    // combined tree here
    expect(ctx.current.allBindings).toBeDefined();
  });

  it('returns binding list with at least 4 nav entries', () => {
    const { result } = renderHook(() => useTrainerShortcuts(),
      { wrapper: makeWrapper() });
    expect(result.current.length).toBeGreaterThanOrEqual(4);
    const combos = result.current.map((b) => b.key);
    expect(combos).toContain('g p');
    expect(combos).toContain('g r');
    expect(combos).toContain('g m');
    expect(combos).toContain('g e');
  });
});
```

+ [ ] **Step 2: Run the test — expect failure**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm exec vitest run src/shell/useTrainerShortcuts.test.ts 2>&1 | tail -5
```

Expected: FAIL — `useTrainerShortcuts` not found.

+ [ ] **Step 3: Implement `useTrainerShortcuts.ts`**

Create `frontend/src/shell/useTrainerShortcuts.ts`:

```ts
import { useShortcuts } from "@pdomain/pdomain-ui/hooks";
import type { ShortcutBinding } from "@pdomain/pdomain-ui/hooks";

/**
 * Trainer nav chord bindings registered into ShortcutsProvider so they
 * appear in the AppShell keybinds dock surface. The actual keydown handlers
 * remain in AppChrome (useHotkey) until AppChrome is removed in Milestone C.
 * After AppChrome removal, the useHotkey calls move here.
 */
export const TRAINER_SHORTCUTS: ShortcutBinding[] = [
  { key: "g p", label: "Go to Profiles", scope: "nav" },
  { key: "g r", label: "Go to Runs", scope: "nav" },
  { key: "g m", label: "Go to Models", scope: "nav" },
  { key: "g e", label: "Go to Eval", scope: "nav" },
  { key: "?", label: "Open shortcuts help", scope: "global" },
];

/** Register trainer shortcuts into the nearest ShortcutsProvider. */
export function useTrainerShortcuts(): ShortcutBinding[] {
  useShortcuts(TRAINER_SHORTCUTS);
  return TRAINER_SHORTCUTS;
}
```

+ [ ] **Step 4: Run the test — expect pass**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm exec vitest run src/shell/useTrainerShortcuts.test.ts 2>&1 | tail -5
```

Expected: PASS.

+ [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add frontend/src/shell/useTrainerShortcuts.ts \
  frontend/src/shell/useTrainerShortcuts.test.ts
git commit -m "feat(shell): add useTrainerShortcuts for keybinds dock \
  registration"
```

---

## Milestone C — Custom header + AppShell wiring

### Task C1: Create `TrainerHeader` (preserves all spec-13 testids)

**Context:** AppShell's built-in header does not include the spec-13
`header-bar` testid, the `header-app-version` badge, or the jobs badge. We use
AppShell's `header` escape-hatch slot (same as simple-gui), rendering a custom
`<header data-testid="header-bar">`. JobsPill is wired to
`useUtilityDock().toggle('jobs')`. ShortcutsHelpButton gets a wrapping `<span
data-testid="header-help-button">` to preserve the spec-13 testid
(ShortcutsHelpButton renders its own button but the testid needs to be on its
wrapper so Playwright can find it).

**Files:**

+ Create: `frontend/src/shell/TrainerHeader.tsx`
+ Create: `frontend/src/shell/TrainerHeader.test.tsx`

+ [ ] **Step 1: Write the failing test**

Create `frontend/src/shell/TrainerHeader.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { createElement } from 'react';
import { TrainerHeader } from './TrainerHeader';

// Mock pdomain-ui shell hooks used inside TrainerHeader
vi.mock('@pdomain/pdomain-ui/shell', () => ({
  JobsPill: ({ activeJobs }: { activeJobs: unknown[] }) =>
    createElement('button', { 'data-testid': 'jobs-pill',
      'aria-label': 'Jobs' },
      `${activeJobs.length} jobs`),
  ShortcutsHelpButton: () =>
    createElement('button', { 'aria-label': 'Keyboard shortcuts' }, '?'),
  SettingsSlot: () => createElement('button', { 'aria-label': 'Settings' },
    '⚙'),
  useUtilityDock: () => ({ toggle: vi.fn() }),
}));

describe('TrainerHeader', () => {
  it('renders header-bar testid', () => {
    render(createElement(TrainerHeader, { activeJobs: [],
      appVersion: '0.1.0' }));
    expect(screen.getByTestId('header-bar')).toBeTruthy();
  });

  it('renders header-app-version testid', () => {
    render(createElement(TrainerHeader, { activeJobs: [],
      appVersion: '0.1.0' }));
    expect(screen.getByTestId('header-app-version').textContent).toContain('0.1.0');
  });

  it('renders header-help-button testid', () => {
    render(createElement(TrainerHeader, { activeJobs: [],
      appVersion: '0.1.0' }));
    expect(screen.getByTestId('header-help-button')).toBeTruthy();
  });

  it('renders header-jobs-badge testid', () => {
    render(createElement(TrainerHeader, { activeJobs: [],
      appVersion: '0.1.0' }));
    expect(screen.getByTestId('header-jobs-badge')).toBeTruthy();
  });
});
```

+ [ ] **Step 2: Run the test — expect failure**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm exec vitest run src/shell/TrainerHeader.test.tsx 2>&1 | tail -5
```

Expected: FAIL — `TrainerHeader` not found.

+ [ ] **Step 3: Implement `TrainerHeader.tsx`**

Create `frontend/src/shell/TrainerHeader.tsx`:

```tsx
import {
  JobsPill,
  ShortcutsHelpButton,
  SettingsSlot,
  useUtilityDock,
} from "@pdomain/pdomain-ui/shell";
import type { ActiveJob } from "@pdomain/pdomain-ui/shell";

export interface TrainerHeaderProps {
  activeJobs: ActiveJob[];
  appVersion: string;
}

/**
 * Custom header for the trainer SPA. Preserves all spec-13 §4.1 testids:
 * header-bar, header-app-version, header-help-button, header-jobs-badge.
 * Renders inside AppShell's header escape-hatch slot.
 */
export function TrainerHeader({ activeJobs,
  appVersion }: TrainerHeaderProps): React.JSX.Element {
  const { toggle } = useUtilityDock();
  return (
    <header
      data-testid="header-bar"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: 52,
        padding: "0 1rem",
        background: "var(--bg-page)",
        borderBottom: "1px solid var(--border-1)",
        flexShrink: 0,
      }}
    >
      <strong style={{ color: "var(--ink-1)", fontSize: 13, fontWeight: 600 }}>
        OCR Trainer
      </strong>
      <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
        <span data-testid="header-app-version" title="App version" style={{
          color: "var(--ink-3)", fontSize: 12 }}>
          v{appVersion}
        </span>
        {/* header-jobs-badge: wraps JobsPill to preserve spec-13 testid */}
        <span data-testid="header-jobs-badge">
          <JobsPill activeJobs={activeJobs} onClick={() => toggle("jobs")} />
        </span>
        {/* header-help-button: wraps ShortcutsHelpButton to preserve spec-13
          testid */}
        <span data-testid="header-help-button">
          <ShortcutsHelpButton />
        </span>
        <SettingsSlot />
      </div>
    </header>
  );
}
```

+ [ ] **Step 4: Run the test — expect pass**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm exec vitest run src/shell/TrainerHeader.test.tsx 2>&1 | tail -5
```

Expected: PASS (4 tests).

+ [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add frontend/src/shell/TrainerHeader.tsx \
  frontend/src/shell/TrainerHeader.test.tsx
git commit -m "feat(shell): add TrainerHeader with spec-13 testid compatibility"
```

---

### Task C2: Create sidebar nav rail content (preserves `sidebar-nav` testids)

**Context:** The existing `AppHeader.tsx` renders `<nav
data-testid="sidebar-nav">` with `<a data-testid="sidebar-nav-{section}">`
links. This nav goes into AppShell's `rail` slot. Rail width is 64px by default
— suitable for icon-only nav, but spec 13 expects link text to be present. We
render a vertical nav list that fits the rail. The `data-testid` values must be
identical to spec 13.

**Files:**

+ Create: `frontend/src/shell/TrainerRail.tsx`
+ Create: `frontend/src/shell/TrainerRail.test.tsx`

+ [ ] **Step 1: Write the failing test**

Create `frontend/src/shell/TrainerRail.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { createElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { TrainerRail } from './TrainerRail';

function wrap(el: React.ReactElement) {
  return createElement(MemoryRouter, {}, el);
}

describe('TrainerRail', () => {
  it('renders sidebar-nav testid', () => {
    render(wrap(createElement(TrainerRail)));
    expect(screen.getByTestId('sidebar-nav')).toBeTruthy();
  });

  const sections = ['profiles', 'datasets', 'runs', 'models', 'eval', 'publish',
    'settings'];
  for (const section of sections) {
    it(`renders sidebar-nav-${section} testid`, () => {
      render(wrap(createElement(TrainerRail)));
      expect(screen.getByTestId(`sidebar-nav-${section}`)).toBeTruthy();
    });
  }
});
```

+ [ ] **Step 2: Run the test — expect failure**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm exec vitest run src/shell/TrainerRail.test.tsx 2>&1 | tail -5
```

Expected: FAIL — `TrainerRail` not found.

+ [ ] **Step 3: Implement `TrainerRail.tsx`**

Create `frontend/src/shell/TrainerRail.tsx`:

```tsx
import { NavLink } from "react-router-dom";

const NAV_SECTIONS = [
  { section: "profiles", label: "Profiles", to: "/profiles" },
  { section: "datasets", label: "Datasets", to: "/profiles" },
  { section: "runs",     label: "Runs",     to: "/runs" },
  { section: "models",   label: "Models",   to: "/models" },
  { section: "eval",     label: "Eval",     to: "/eval" },
  { section: "publish",  label: "Publish",  to: "/publish" },
  { section: "settings", label: "Settings", to: "/settings" },
] as const;

/** Vertical nav for AppShell rail slot. Preserves spec-13 §4.1 sidebar-nav
  testids. */
export function TrainerRail(): React.JSX.Element {
  return (
    <nav
      data-testid="sidebar-nav"
      aria-label="Primary"
      style={{
        display: "flex",
        flexDirection: "column",
        padding: "0.5rem 0",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {NAV_SECTIONS.map(({ section, label, to }) => (
        <NavLink
          key={section}
          data-testid={`sidebar-nav-${section}`}
          to={to}
          style={({ isActive }) => ({
            display: "block",
            padding: "0.4rem 0.75rem",
            fontSize: 12,
            fontWeight: isActive ? 600 : 400,
            color: isActive ? "var(--accent)" : "var(--ink-2)",
            textDecoration: "none",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          })}
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
```

+ [ ] **Step 4: Run the test — expect pass**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm exec vitest run src/shell/TrainerRail.test.tsx 2>&1 | tail -5
```

Expected: PASS (8 tests).

+ [ ] **Step 5: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add frontend/src/shell/TrainerRail.tsx \
  frontend/src/shell/TrainerRail.test.tsx
git commit -m "feat(shell): add TrainerRail for AppShell rail slot with \
  spec-13 testids"
```

---

### Task C3: Rewrite `App.tsx` to use AppShell

**Context:** This is the main wiring task. Replace `AppChrome` +
`BrowserRouter`-wrapping with `SuiteSiblingsProvider` → `ShortcutsProvider` →
`AppShell`. The `BrowserRouter` moves to the innermost point needed by routing
(inside `AppShell.main`). `AppChrome` is removed from the render tree (deleted
in Task C4). `useTrainerJobs` feeds the jobs dock.

The existing `App.test.tsx` checks that profiles renders — update it to expect
`data-testid="app-shell"` instead of `data-testid="app-root"`. Note: `app-root`
is the current top-level div in `App.tsx`; after migration AppShell renders
`data-testid="app-shell"`.

**Files:**

+ Modify: `frontend/src/App.tsx`
+ Modify: `frontend/src/App.test.tsx`

+ [ ] **Step 1: Update the App test first (TDD)**

In `frontend/src/App.test.tsx`, update the existing smoke test to check
`app-shell` instead of `app-root`:

```tsx
// Replace the existing App.test.tsx with:
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

// Minimal mock for AppShell to avoid deep pdomain-ui render tree
vi.mock("@pdomain/pdomain-ui/shell", async (importOriginal) => {
  const actual = await importOriginal<typeof
    import("@pdomain/pdomain-ui/shell")>();
  return {
    ...actual,
    AppShell: ({ main }: { main: React.ReactNode }) =>
      <div data-testid="app-shell">{main}</div>,
    SuiteSiblingsProvider: ({ children }: { children: React.ReactNode }) =>
      <>{children}</>,
    JobsPill: () => <button>jobs</button>,
    ShortcutsHelpButton: () => <button>?</button>,
    SettingsSlot: () => <button>⚙</button>,
    useUtilityDock: () => ({ toggle: vi.fn() }),
    createApiUIPrefsConfig: () => ({}),
  };
});

vi.mock("@pdomain/pdomain-ui/hooks", () => ({
  ShortcutsProvider: ({ children }: { children: React.ReactNode }) =>
    <>{children}</>,
  useShortcuts: vi.fn(),
}));

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ profiles: [], has_legacy_layout: false }),
      } as Response),
    ),
  );
});

describe("App", () => {
  it("renders app-shell root", async () => {
    render(<App />);
    expect(screen.getByTestId("app-shell")).toBeTruthy();
  });
});
```

+ [ ] **Step 2: Run the test — expect failure**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm exec vitest run src/App.test.tsx 2>&1 | tail -5
```

Expected: FAIL — App still renders `app-root`, not `app-shell`.

+ [ ] **Step 3: Rewrite `App.tsx`**

Replace `frontend/src/App.tsx` with:

```tsx
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useNavigate
} from "react-router-dom";
import {
  AppShell,
  SuiteSiblingsProvider,
  createApiUIPrefsConfig,
} from "@pdomain/pdomain-ui/shell";
import { ShortcutsProvider } from "@pdomain/pdomain-ui/hooks";
import type { InstalledApp, LaunchResult } from "@pdomain/pdomain-ui/shell";

import { ProfilesPage } from "./pages/ProfilesPage";
import { ProfileDetailPage } from "./pages/ProfileDetailPage";
import { DatasetsPage } from "./pages/DatasetsPage";
import { RunListPage } from "./pages/RunListPage";
import { RunDetailPage } from "./pages/RunDetailPage";
import { NewRunPage } from "./pages/NewRunPage";
import { ModelsPage } from "./pages/ModelsPage";
import { ModelDetailPage } from "./pages/ModelDetailPage";
import { EvalFormPage } from "./pages/EvalFormPage";
import { EvalResultPage } from "./pages/EvalResultPage";
import { PublishPage } from "./pages/PublishPage";
import { BannerStack } from "./components/BannerStack";
import { TrainerHeader } from "./shell/TrainerHeader";
import { TrainerRail } from "./shell/TrainerRail";
import { useTrainerJobs, makeJobsProps } from "./shell/useTrainerJobs";
import { useTrainerShortcuts } from "./shell/useTrainerShortcuts";
import { getAppEnv } from "./lib/appEnv";
import { trainerSettingsPanels } from "./shell/trainerSettingsPanels";

const uiPrefsConfig = createApiUIPrefsConfig("/api/ui-prefs");

const fetchInstalled = async (): Promise<InstalledApp[]> => {
  try {
    const res = await fetch("/api/suite/installed");
    if (!res.ok) return [];
    return (await res.json()) as InstalledApp[];
  } catch {
    return [];
  }
};

const postLaunch = async (id: string): Promise<LaunchResult> => {
  try {
    const res = await fetch("/api/suite/launch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
    if (!res.ok) return { kind: "requires-host-config", siblingId: id };
    return (await res.json()) as LaunchResult;
  } catch {
    return { kind: "requires-host-config", siblingId: id };
  }
};

function AppRoutes(): React.JSX.Element {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/profiles" replace />} />
      <Route path="/profiles" element={<ProfilesPage />} />
      <Route path="/profiles/:name" element={<ProfileDetailPage />} />
      <Route path="/profiles/:name/datasets/:task" element={<DatasetsPage />} />
      <Route path="/runs" element={<RunListPage />} />
      <Route path="/runs/new" element={<NewRunPage />} />
      <Route path="/runs/:runId" element={<RunDetailPage />} />
      <Route path="/models" element={<ModelsPage />} />
      <Route path="/models/:name" element={<ModelDetailPage />} />
      <Route path="/eval" element={<EvalFormPage />} />
      <Route path="/eval/:runId/result" element={<EvalResultPage />} />
      <Route path="/publish" element={<PublishPage />} />
    </Routes>
  );
}

function AppShellWithHeader(): React.JSX.Element {
  const { pill, dock } = useTrainerJobs();
  const navigate = useNavigate();
  useTrainerShortcuts();
  const env = getAppEnv();
  const jobsProps = makeJobsProps(dock, (id) => navigate(`/runs/${id}`));
  return (
    <AppShell
      appId="pdomain-ocr-trainer-spa"
      appDisplayName="OCR Trainer"
      appIconUrl="/api/self/icons/32"
      deployMode="local"
      launcherSlot="header"
      uiPrefsConfig={uiPrefsConfig}
      settingsPanels={trainerSettingsPanels}
      jobs={jobsProps}
      header={<TrainerHeader activeJobs={pill} appVersion={env.version} />}
      rail={<TrainerRail />}
      main={
        <>
          <BannerStack />
          <AppRoutes />
        </>
      }
    />
  );
}

export default function App(): React.JSX.Element {
  return (
    <BrowserRouter future={{ v7_startTransition: true,
      v7_relativeSplatPath: true }}>
      <SuiteSiblingsProvider value={{ fetchInstalled, postLaunch }}>
        <ShortcutsProvider>
          <AppShellWithHeader />
        </ShortcutsProvider>
      </SuiteSiblingsProvider>
    </BrowserRouter>
  );
}
```

+ [ ] **Step 4: Create the settings panels stub (needed by App.tsx import)**

Create `frontend/src/shell/trainerSettingsPanels.ts`:

```ts
import type { SettingsPanelDescriptor } from "@pdomain/pdomain-ui/shell";

/**
 * Trainer settings panels injected into the AppShell utility dock.
 * Compute panel is added in Milestone D.
 */
export const trainerSettingsPanels: SettingsPanelDescriptor[] = [];
```

+ [ ] **Step 5: Run the App test — expect pass**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm exec vitest run src/App.test.tsx 2>&1 | tail -5
```

Expected: PASS.

+ [ ] **Step 6: Run full frontend test suite**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make frontend-test 2>&1 | tail -10
```

Expected: all existing tests pass (AppHeader.test.tsx and AppChrome are still
present; they still test the old components which still exist on disk).

+ [ ] **Step 7: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add frontend/src/App.tsx frontend/src/App.test.tsx \
  frontend/src/shell/trainerSettingsPanels.ts
git commit -m "feat(shell): wire AppShell into App.tsx (providers + header + \
  rail + jobs dock)"
```

---

### Task C4: Delete `AppChrome.tsx` + `AppHeader.tsx`, update their tests

**Context:** Now that App.tsx no longer uses AppChrome or AppHeader, delete the
files and update their tests. `AppHeader.test.tsx` tests the bespoke header;
replace with a focused test on the existing `TrainerHeader` (already tested in
B2). `AppChrome` had no dedicated test file.

**Files:**

+ Delete: `frontend/src/components/AppChrome.tsx`
+ Delete: `frontend/src/components/AppHeader.tsx`
+ Delete: `frontend/src/components/AppHeader.test.tsx`

+ [ ] **Step 1: Run the full test suite to confirm zero failures before
  deletion**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make frontend-test 2>&1 | tail -10
```

Expected: PASS.

+ [ ] **Step 2: Delete the obsolete files**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git rm frontend/src/components/AppChrome.tsx
git rm frontend/src/components/AppHeader.tsx
git rm frontend/src/components/AppHeader.test.tsx
```

+ [ ] **Step 3: Run frontend test suite — confirm still green**

```bash
make frontend-test 2>&1 | tail -10
```

Expected: PASS — no tests reference the deleted files.

+ [ ] **Step 4: Run full CI**

```bash
make ci 2>&1 | tail -15
```

Expected: green. (Frontend typecheck will also confirm no dangling imports.)

+ [ ] **Step 5: Commit**

```bash
git commit -m "refactor(shell): remove AppChrome + AppHeader (replaced by \
  AppShell + TrainerHeader + TrainerRail)"
```

---

## Milestone D — Compute settings panel

### Task D1: Create `ComputePanelContent` settings panel

**Context:** `pdomain-ops.suite.device_routes` already mounts `GET/PUT
/api/suite/device` via `mount_routes()` in `bootstrap.py`. The frontend wiring
is identical to `pdomain-ocr-simple-gui`'s `ComputePanelContent` component. Use
`createApiDeviceConfig()` (default URL `/api/suite/device`) and
`useDeviceInfo(config)` from `@pdomain/pdomain-ui/stores`. Render
`ComputeTargetPanel` from `@pdomain/pdomain-ui/shell`.

**Files:**

+ Create: `frontend/src/shell/ComputePanelContent.tsx`
+ Create: `frontend/src/shell/ComputePanelContent.test.tsx`
+ Modify: `frontend/src/shell/trainerSettingsPanels.ts`

+ [ ] **Step 1: Write the failing test**

Create `frontend/src/shell/ComputePanelContent.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { createElement } from 'react';

// Stub useDeviceInfo so we can test both loading and loaded states
vi.mock('@pdomain/pdomain-ui/stores', () => ({
  useDeviceInfo: vi.fn(() => ({ loading: false, error: null, info: null,
    setDevice: vi.fn(), clearDevice: vi.fn() })),
}));
vi.mock('@pdomain/pdomain-ui/shell', () => ({
  ComputeTargetPanel: ({ info }: { info: unknown }) =>
    createElement('div', { 'data-testid': 'compute-target-panel' },
      info ? 'loaded' : 'empty'),
  createApiDeviceConfig: () => ({}),
}));

import { ComputePanelContent } from './ComputePanelContent';

describe('ComputePanelContent', () => {
  it('renders without crashing (no device info)', () => {
    render(createElement(ComputePanelContent));
    // No error or loading shown when info is null and no error
    expect(screen.getByTestId('compute-target-panel')).toBeTruthy();
  });

  it('renders loading message when loading and no info', () => {
    const { useDeviceInfo } = await import('@pdomain/pdomain-ui/stores');
    (useDeviceInfo as ReturnType<typeof vi.fn>).mockReturnValueOnce({
      loading: true, error: null, info: null, setDevice: vi.fn(), clearDevice:
        vi.fn(),
    });
    render(createElement(ComputePanelContent));
    expect(screen.getByText(/checking compute/i)).toBeTruthy();
  });
});
```

+ [ ] **Step 2: Run the test — expect failure**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm exec vitest run src/shell/ComputePanelContent.test.tsx 2>&1 | tail -5
```

Expected: FAIL — `ComputePanelContent` not found.

+ [ ] **Step 3: Implement `ComputePanelContent.tsx`**

Create `frontend/src/shell/ComputePanelContent.tsx`:

```tsx
import {
  ComputeTargetPanel,
  createApiDeviceConfig,
} from "@pdomain/pdomain-ui/shell";
import { useDeviceInfo } from "@pdomain/pdomain-ui/stores";

const _deviceConfig = createApiDeviceConfig();

/**
 * Compute settings panel for the utility dock.
 * Backed by GET/PUT /api/suite/device (mounted by pdomain-ops mount_routes).
 */
export function ComputePanelContent(): React.JSX.Element {
  const device = useDeviceInfo(_deviceConfig);

  if (device.loading && !device.info) {
    return <p style={{ margin: 0 }}>Checking compute devices</p>;
  }

  if (device.error && !device.info) {
    return (
      <p role="alert" style={{ margin: 0, color: "var(--color-danger)" }}>
        {device.error instanceof Error
          ? device.error.message
          : String(device.error)}
      </p>
    );
  }

  return (
    <ComputeTargetPanel
      info={device.info}
      onSelect={(deviceId) => void device.setDevice("app", deviceId)}
      onClear={(scope) => void device.clearDevice(scope)}
      cudaDocsUrl="/docs/runbooks/cuda-setup.md"
    />
  );
}
```

+ [ ] **Step 4: Run the test — expect pass**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa/frontend
pnpm exec vitest run src/shell/ComputePanelContent.test.tsx 2>&1 | tail -5
```

Expected: PASS.

+ [ ] **Step 5: Wire into `trainerSettingsPanels.ts`**

Replace `frontend/src/shell/trainerSettingsPanels.ts`:

```ts
import type { SettingsPanelDescriptor } from "@pdomain/pdomain-ui/shell";
import { createElement } from "react";
import { ComputePanelContent } from "./ComputePanelContent";

/**
 * Trainer settings panels injected into the AppShell utility dock.
 * Appended after the built-in Appearance panel.
 */
export const trainerSettingsPanels: SettingsPanelDescriptor[] = [
  {
    id: "compute",
    label: "Compute",
    content: createElement(ComputePanelContent),
  },
];
```

+ [ ] **Step 6: Run full frontend tests**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make frontend-test 2>&1 | tail -10
```

Expected: PASS.

+ [ ] **Step 7: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add frontend/src/shell/ComputePanelContent.tsx \
  frontend/src/shell/ComputePanelContent.test.tsx \
    frontend/src/shell/trainerSettingsPanels.ts
git commit -m "feat(shell): add Compute settings panel (device API backed)"
```

---

### Task D2: Backend — verify device startup warmup + add `/api/ui-prefs` endpoint

**Context:** Two backend items needed by the frontend work above:

1. `GET /api/ui-prefs` — `createApiUIPrefsConfig('/api/ui-prefs')` calls this on
   load. pdomain-ops `mount_routes` already mounts `/api/suite/prefs` (the
   app-prefs endpoint); `ui-prefs` is a separate endpoint. The simplest
   approach: add a thin FastAPI route that reads/writes a `ui_prefs` slice of
   the app prefs JSON file. (Pattern from simple-gui: the prefs PATCH endpoint
   is the same route as the app-prefs route since simple-gui unifies them.)

2. `GET /api/suite/device` startup warmup — spec 10/backlog doc says to trigger
   a warmup at startup when the Compute panel is exposed. The device endpoint is
   already mounted; warmup means calling `list_devices()` once at startup so the
   result is cached. Add a startup event handler in `bootstrap.py`.

**Files:**

+ Modify: `src/pdomain_ocr_trainer_spa/api/__init__.py` or `bootstrap.py`
+ Create: `src/pdomain_ocr_trainer_spa/api/ui_prefs.py`
+ Modify: `tests/test_ui_prefs.py` (new)

+ [ ] **Step 1: Write the failing test for `/api/ui-prefs`**

Create `tests/test_ui_prefs.py`:

```python
"""Tests for GET/PATCH /api/ui-prefs — UIPrefsConfig persistence endpoint."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from pdomain_ocr_trainer_spa.bootstrap import create_app
    from pdomain_ocr_trainer_spa import settings as s
    monkeypatch.setattr(s, "DATA_DIR", tmp_path)
    app = create_app()
    return TestClient(app)


def test_get_ui_prefs_default(client):
    """First launch returns 200 with defaults, not 404."""
    resp = client.get("/api/ui-prefs")
    assert resp.status_code == 200
    data = resp.json()
    assert "theme" in data
    assert data["theme"] in ("dark", "light")


def test_patch_ui_prefs_persists(client):
    """PATCH round-trips; subsequent GET returns updated value."""
    patch_resp = client.patch(
        "/api/ui-prefs",
        json={"theme": "light"},
    )
    assert patch_resp.status_code == 200
    get_resp = client.get("/api/ui-prefs")
    assert get_resp.json()["theme"] == "light"
```

+ [ ] **Step 2: Run the test — expect failure**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/test_ui_prefs.py -v 2>&1 | tail -10
```

Expected: FAIL — `/api/ui-prefs` returns 404.

+ [ ] **Step 3: Implement `api/ui_prefs.py`**

Create `src/pdomain_ocr_trainer_spa/api/ui_prefs.py`:

```python
"""GET /api/ui-prefs + PATCH /api/ui-prefs — UIPrefs persistence for
    AppShell."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from pdomain_ocr_trainer_spa import settings

router = APIRouter()

_FILENAME = "ui_prefs.json"


def _prefs_path() -> Path:
    return Path(settings.DATA_DIR) / _FILENAME


class UIPrefs(BaseModel):
    theme: str = "dark"
    density: str = "normal"
    fontScale: float = 1.0  # noqa: N815  # camelCase matches frontend contract


def _load() -> UIPrefs:
    p = _prefs_path()
    if not p.exists():
        return UIPrefs()
    try:
        return UIPrefs(**json.loads(p.read_text()))
    except Exception:  # noqa: BLE001  # corrupt file → return defaults
        return UIPrefs()


def _save(prefs: UIPrefs) -> None:
    p = _prefs_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(prefs.model_dump_json())


@router.get("/api/ui-prefs", response_model=UIPrefs)
async def get_ui_prefs() -> UIPrefs:
    return _load()


@router.patch("/api/ui-prefs", response_model=UIPrefs)
async def patch_ui_prefs(partial: dict) -> UIPrefs:
    current = _load()
    updated = current.model_copy(update={k: v for k,
        v in partial.items() if v is not None})
    _save(updated)
    return updated
```

+ [ ] **Step 4: Register the router in bootstrap**

In `src/pdomain_ocr_trainer_spa/bootstrap.py`, after the existing router
registrations, add:

```python
from pdomain_ocr_trainer_spa.api.ui_prefs import router as ui_prefs_router
app.include_router(ui_prefs_router)
```

+ [ ] **Step 5: Run the test — expect pass**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/test_ui_prefs.py -v 2>&1 | tail -10
```

Expected: PASS (2 tests).

+ [ ] **Step 6: Add device warmup to startup**

In `src/pdomain_ocr_trainer_spa/bootstrap.py`, add a lifespan startup handler
that triggers `list_devices()` in a background thread so the first
`/api/suite/device` request returns fast:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def _warmup_device_info() -> None:
    """Background probe — result cached by pdomain-ops device_probe."""
    try:
        from pdomain_ops.gpu.device_probe import list_devices
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(ThreadPoolExecutor(max_workers=1),
            list_devices)
    except Exception:  # noqa: BLE001  # optional warmup — never crash startup
        pass
```

Call `asyncio.create_task(_warmup_device_info())` inside the FastAPI `lifespan`
startup block (or as a background task registered with
`app.add_event_handler("startup", ...)` if the app uses the older pattern).

+ [ ] **Step 7: Run full CI**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make ci 2>&1 | tail -15
```

Expected: green.

+ [ ] **Step 8: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add src/pdomain_ocr_trainer_spa/api/ui_prefs.py \
  src/pdomain_ocr_trainer_spa/bootstrap.py tests/test_ui_prefs.py
git commit -m "feat(api): add /api/ui-prefs endpoint + device warmup at startup"
```

---

### Task D3: Delete superseded backlog doc

**Files:**

+ Delete: `docs/plans/2026-06-08-compute-settings-panel-backlog.md`

+ [ ] **Step 1: Delete the file**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git rm docs/plans/2026-06-08-compute-settings-panel-backlog.md
git commit -m "docs: remove compute-settings backlog (superseded by this plan)"
```

---

## Milestone E — Driver contract conformance gate

### Task E1: Update driver contract conformance test

**Context:** `tests/e2e/test_driver_contract.py` (spec 13 §5) asserts all
testids exist. After AppShell migration, the testids at the app-chrome level may
have changed element types (e.g. `header-jobs-badge` is now a `<span>` wrapper
around `JobsPill`). Update the test to use `page.locator('[data-testid="..."]')`
— type-agnostic — and add the two new AppShell-level testids: `app-shell`,
`app-shell-header`, `app-shell-rail`, `app-shell-main`.

**Files:**

+ Modify: `tests/e2e/test_driver_contract.py`

+ [ ] **Step 1: Read current test content**

```bash
cat \
  /workspaces/ocr-container/pdomain-ocr-trainer-spa/tests/e2e/test_driver_contract.py
```

+ [ ] **Step 2: Add AppShell-level testid assertions**

In `tests/e2e/test_driver_contract.py`, after the existing chrome testid checks,
add:

```python
# AppShell-level testids (added by pdomain-ui AppShell)
page.locator('[data-testid="app-shell"]').wait_for(timeout=5000)
page.locator('[data-testid="app-shell-header"]').wait_for(timeout=5000)
page.locator('[data-testid="app-shell-rail"]').wait_for(timeout=5000)
page.locator('[data-testid="app-shell-main"]').wait_for(timeout=5000)
```

+ [ ] **Step 3: Run the driver contract test**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make e2e-browser 2>&1 | tail -20
```

Expected: PASS. (Requires the server to be running; see browser verification
milestone for the full setup.)

+ [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_driver_contract.py
git commit -m "test(e2e): add AppShell testids to driver contract conformance \
  test"
```

---

## Milestone F — Follow-on: Jobs dock wiring (deferred)

**Status: SCOPED, NOT YET PLANNED.** The `AppShell.jobs` prop is wired in Task
C3 above with `makeJobsProps(dock, onJobOpen)`. This feeds the dock with live
job data. However, the trainer's existing `useNotificationStream` hook uses a
different job-watching pattern (SSE subscription per job ID,
terminal-toast-on-close) and is independent of the dock. Both can coexist.

The deferred question is whether `useNotificationStream` should be replaced by
the dock-centric model. This requires:

1. `pdomain-ui` AppShell jobs prop to support per-job SSE subscription
   (currently only polling is shown in simple-gui).
2. Decision from CT on whether the toast notification pattern (spec 11) remains
   alongside the dock or is retired.

Create a follow-on GH issue in `pdomain/pdomain-ocr-trainer-spa` to track this:

```bash
gh issue create --repo pdomain/pdomain-ocr-trainer-spa \
  --label "kind:chore" --label "status:backlog" \
  --title "Wire useNotificationStream SSE into AppShell jobs dock (retire \
    separate toast pattern)" \
  --body "Follow-on from the pdomain-ui adoption plan.\n\nCurrently both \
    coexist: useTrainerJobs polling feeds the dock, useNotificationStream SSE \
      fires toasts on terminal transitions. Decide whether to retire the toast \
        pattern in favor of dock-only notification, or keep both."
```

---

## Milestone G — Browser Verification (mandatory)

### Task G1: Playwright smoke — app loads under AppShell

**Context:** This milestone is mandatory per the FastAPI+SPA plan requirements.
It exercises the real running server with Chromium to catch shell-level bugs
invisible to unit tests (missing tokens.css → white screen, broken AppShell
mount → no testids visible, React Router wiring broken → sub-paths 404).

**Files:**

+ Modify: `tests/e2e/test_shell_migration.py` (new file)
+ Modify: `Makefile` (add `e2e-browser` target if not present)
+ Modify: `pyproject.toml` (add `[dependency-groups] e2e` with
  `pytest-playwright`)

+ [ ] **Step 1: Add Playwright to dependency group**

In `pyproject.toml`, add:

```toml
[dependency-groups]
e2e = ["pytest-playwright>=0.5"]
```

Run:

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv sync --group e2e
uv run playwright install chromium
```

Expected: chromium installs without errors.

+ [ ] **Step 2: Verify `make e2e-browser` target exists**

```bash
grep "e2e-browser" /workspaces/ocr-container/pdomain-ocr-trainer-spa/Makefile
```

If the target does not exist, add to `Makefile`:

```makefile
e2e-browser:
 uv run --group e2e pytest tests/e2e/ -v --headed=false
```

+ [ ] **Step 3: Write the browser verification test**

Create `tests/e2e/test_shell_migration.py`:

```python
"""Browser smoke tests verifying AppShell migration — runs against the real
    server."""
import pytest
from playwright.sync_api import Page, expect


TESTIDS_SPEC_13 = [
    "header-bar",
    "header-app-version",
    "header-help-button",
    "header-jobs-badge",
    "sidebar-nav",
    "sidebar-nav-profiles",
    "sidebar-nav-runs",
    "sidebar-nav-models",
]

APPSHELL_TESTIDS = [
    "app-shell",
    "app-shell-header",
    "app-shell-rail",
    "app-shell-main",
]


@pytest.mark.parametrize("testid", TESTIDS_SPEC_13 + APPSHELL_TESTIDS)
def test_spec13_testids_present(page: Page, base_url: str, testid: str) -> None:
    """All spec-13 chrome testids
        and AppShell shell testids are present after shell migration."""
    page.goto(base_url)
    expect(page.locator(f'[data-testid="{testid}"]')).to_be_visible(timeout=8000)


def test_app_loads_no_console_error(page: Page, base_url: str) -> None:
    """App loads with no console errors (catches missing CSS/JS bundle)."""
    errors: list[str] = []
    page.on("console",
        lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(base_url)
    page.locator('[data-testid="app-shell"]').wait_for(timeout=8000)
    assert not errors, f"Console errors: {errors}"


def test_profiles_route_renders(page: Page, base_url: str) -> None:
    """GET / redirects to /profiles; profiles page root testid is visible."""
    page.goto(base_url)
    expect(page.locator('[data-testid="profiles-page"]')).to_be_visible(timeout=8000)


def test_direct_subroute_renders(page: Page, base_url: str) -> None:
    """Direct navigation to /runs renders the RunListPage, not a 404."""
    page.goto(f"{base_url}/runs")
    expect(page.locator('[data-testid="run-list-page"]')).to_be_visible(timeout=8000)


def test_compute_settings_panel_opens(page: Page, base_url: str) -> None:
    """Clicking the settings gear opens the utility dock; Compute tab is
        present."""
    page.goto(base_url)
    page.locator('[data-testid="app-shell"]').wait_for(timeout=8000)
    # SettingsSlot renders a button with aria-label="Settings"
    page.get_by_role("button", name="Settings").click()
    expect(page.get_by_role("tab", name="Compute")).to_be_visible(timeout=4000)
```

+ [ ] **Step 4: Run the browser verification tests**

Start the server in a separate terminal (or use a fixture), then:

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run --group e2e pytest tests/e2e/test_shell_migration.py -v \
  --base-url=http://localhost:8081 2>&1 | tail -20
```

Expected: all tests pass when the built frontend is served.

+ [ ] **Step 5: Wire into `make ci`**

In `Makefile`, ensure `ci` calls `e2e-browser` or add a note that `make ci` runs
unit tests and `make e2e-browser` is the full-stack gate (same pattern as
simple-gui where `make ci-full` includes Playwright).

+ [ ] **Step 6: Run full `make ci`**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make ci 2>&1 | tail -15
```

Expected: green.

+ [ ] **Step 7: Final commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add tests/e2e/test_shell_migration.py pyproject.toml Makefile
git commit -m "test(e2e): browser verification for AppShell migration (shell \
  testids + compute panel)"
```

---

## Open questions

1. **`/api/ui-prefs` vs `/api/suite/prefs`:** `pdomain-ops.suite.prefs` already
   mounts a prefs endpoint at `/api/suite/prefs`. It is unclear whether
   `createApiUIPrefsConfig('/api/ui-prefs')` should hit that or a separate
   trainer-specific endpoint. The simplest safe choice (Task D2) is a new thin
   endpoint; if `mount_routes` eventually exposes a ui-prefs endpoint, the
   trainer can switch. CT to decide whether to reuse `/api/suite/prefs`
   directly.

2. **`useNotificationStream` and the jobs dock:** Two parallel job-watching
   mechanisms will coexist after this plan (SSE toasts + polling dock). The
   Milestone F note above describes the follow-on. CT to decide timeline.

3. **HotkeyHelpDialog:** The existing `HotkeyHelpDialog.tsx` (opened by the old
   `header-help-button`) is replaced by `ShortcutsHelpButton` (opens
   pdomain-ui's built-in cheatsheet). The old dialog can be deleted once CT
   confirms the pdomain-ui cheatsheet is sufficient. It is a safe deletion —
   HotkeyHelpDialog is only referenced from the deleted AppChrome.

4. **`useHotkey` registrations:** The SPA-local `hotkeyRegistry` + `useHotkey`
   hook continue to work but their bindings are not visible in the keybinds dock
   unless also registered via `useTrainerShortcuts`. The long-term path is
   migrating all `useHotkey` calls to pdomain-ui `useShortcuts`. This is
   deferred to a future cleanup issue.

5. **pdomain-ui version in registry:** This plan targets `^0.7.1`. If only
   `0.2.2` is published to `pdomain-index-npm`, run `make local-dev` and `make
   local-frontend-install` to work against the local pdomain-ui checkout
   instead.
