// Global hotkey registry (spec 12-hotkeys-a11y §1, §8).
//
// Every binding registered via the `useHotkey` wrapper records itself
// here so the `?` help dialog can enumerate the active bindings. The
// registry is a module-level singleton keyed by `scope`; entries are
// reference-counted so React StrictMode's double-mount and hot reloads
// do not leave stale rows.
//
// Snapshots returned to `useSyncExternalStore` are cached and only
// rebuilt on mutation — `getSnapshot` must return a stable reference
// between mutations or React loops.

/** Display order + label for each hotkey scope. */
export interface ScopeMeta {
  /** Stable scope id, e.g. "app", "kanban", "run-detail". */
  scope: string;
  /** Human label shown as a section heading in the help dialog. */
  label: string;
}

/** Ordered scope metadata — the help dialog renders sections in this order. */
export const SCOPE_ORDER: ScopeMeta[] = [
  { scope: "app", label: "Global" },
  { scope: "kanban", label: "Datasets" },
  { scope: "run-detail", label: "Run detail" },
  { scope: "run-form", label: "Run form" },
  { scope: "models-list", label: "Models" },
];

/** One registered hotkey binding. */
export interface HotkeyEntry {
  scope: string;
  /** Key combination as passed to react-hotkeys-hook, e.g. "g p". */
  combo: string;
  /** Human description shown in the help dialog. */
  description: string;
}

/** A scope and its bound hotkey entries. */
export interface HotkeyGroup {
  meta: ScopeMeta;
  entries: HotkeyEntry[];
}

interface RegistryRow extends HotkeyEntry {
  /** Mount reference count — entry is dropped when this reaches 0. */
  refs: number;
}

const rows = new Map<string, RegistryRow>();
const listeners = new Set<() => void>();

let listSnapshot: HotkeyEntry[] = [];
let groupSnapshot: HotkeyGroup[] = [];

function keyOf(scope: string, combo: string): string {
  return `${scope} ${combo}`;
}

function rebuildSnapshots(): void {
  listSnapshot = [...rows.values()].map(({ scope, combo, description }) => ({
    scope,
    combo,
    description,
  }));
  const groups: HotkeyGroup[] = [];
  for (const meta of SCOPE_ORDER) {
    const entries = listSnapshot.filter((e) => e.scope === meta.scope);
    if (entries.length > 0) groups.push({ meta, entries });
  }
  const known = new Set(SCOPE_ORDER.map((m) => m.scope));
  const extra = [...new Set(listSnapshot.map((e) => e.scope))].filter(
    (s) => !known.has(s),
  );
  for (const scope of extra) {
    groups.push({
      meta: { scope, label: scope },
      entries: listSnapshot.filter((e) => e.scope === scope),
    });
  }
  groupSnapshot = groups;
}

function emit(): void {
  rebuildSnapshots();
  for (const listener of listeners) listener();
}

/** Raised when a duplicate (scope, combo) is registered (spec 12 §4). */
export class DuplicateHotkeyError extends Error {
  constructor(scope: string, combo: string) {
    super(`Duplicate hotkey "${combo}" in scope "${scope}"`);
    this.name = "DuplicateHotkeyError";
  }
}

/**
 * Register a hotkey entry. Returns an unregister function.
 *
 * A second *distinct* registration of the same (scope, combo) throws
 * `DuplicateHotkeyError` in dev and logs `console.error` in prod
 * (spec 12 §4). Re-registering the identical entry (StrictMode double
 * mount) just bumps the ref-count.
 */
export function registerHotkey(entry: HotkeyEntry): () => void {
  const key = keyOf(entry.scope, entry.combo);
  const existing = rows.get(key);
  if (existing !== undefined) {
    if (existing.description !== entry.description) {
      const err = new DuplicateHotkeyError(entry.scope, entry.combo);
      if (import.meta.env.DEV) throw err;
      console.error(err.message);
    }
    existing.refs += 1;
  } else {
    rows.set(key, { ...entry, refs: 1 });
    emit();
  }
  return () => {
    const row = rows.get(key);
    if (row === undefined) return;
    row.refs -= 1;
    if (row.refs <= 0) {
      rows.delete(key);
      emit();
    }
  };
}

/** All currently registered hotkey entries (cached snapshot). */
export function listHotkeys(): HotkeyEntry[] {
  return listSnapshot;
}

/** Hotkey entries grouped by scope, ordered per {@link SCOPE_ORDER}. */
export function hotkeysByScope(): HotkeyGroup[] {
  return groupSnapshot;
}

/** Subscribe to registry changes — returns an unsubscribe function. */
export function subscribeHotkeys(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Test-only: clear the registry. */
export function _resetHotkeyRegistry(): void {
  rows.clear();
  emit();
}
