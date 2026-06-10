// Datasets-kanban store — holds the committed KanbanView plus a client-side
// staged overlay layered over it (spec 05 §5, D-T23). Drags/keyboard moves
// mutate the overlay only; `apply` commits the whole diff in one batch.

import { create } from "zustand";
import {
  applyAssignments,
  fetchKanban,
  scanKanban,
  setIncludeToggles,
  type ApplyError,
  type KanbanColumnId,
  type KanbanView,
} from "../api/datasets";

/** The committed column id of a chip key, or undefined when the key is unknown. */
export function committedColumnOf(
  view: KanbanView | null,
  key: string,
): KanbanColumnId | undefined {
  if (!view) return undefined;
  for (const columnId of ["unassigned", "train", "val"] as KanbanColumnId[]) {
    for (const row of view.columns[columnId].rows) {
      if (row.pages.some((chip) => chip.key === key)) return columnId;
    }
  }
  return undefined;
}

export interface DatasetsState {
  profile: string;
  task: string;
  view: KanbanView | null;
  /** chip key -> staged column. Only entries differing from committed truth. */
  staged: Record<string, KanbanColumnId>;
  loading: boolean;
  applying: boolean;
  error: string | null;
  applyErrors: ApplyError[];
  statusMessage: string | null;

  load: (profile: string, task: string) => Promise<void>;
  rescan: () => Promise<void>;
  /** Stage one or more chips into a target column (client-side only). */
  stageMove: (keys: string[], target: KanbanColumnId) => void;
  /** Drop the staged overlay (Discard). */
  discard: () => void;
  /** The effective (staged-or-committed) column of a chip key. */
  effectiveColumnOf: (key: string) => KanbanColumnId | undefined;
  /** Number of chips whose staged column differs from committed. */
  pendingCount: () => number;
  /** Commit the staged diff to the server (Apply). */
  apply: () => Promise<void>;
  toggleInclude: (
    includeDetection: boolean,
    includeRecognition: boolean,
  ) => Promise<void>;
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export const createDatasetsStore = () =>
  create<DatasetsState>((set, get) => ({
    profile: "",
    task: "recognition",
    view: null,
    staged: {},
    loading: false,
    applying: false,
    error: null,
    applyErrors: [],
    statusMessage: null,

    load: async (profile, task) => {
      set({ profile, task, loading: true, error: null, staged: {} });
      try {
        const view = await fetchKanban(profile, task);
        set({ view });
      } catch (err) {
        set({ error: errorMessage(err) });
      } finally {
        set({ loading: false });
      }
    },

    rescan: async () => {
      const { profile, task } = get();
      set({ loading: true, error: null });
      try {
        const view = await scanKanban(profile, task);
        set({ view, staged: {}, applyErrors: [], statusMessage: "Rescanned." });
      } catch (err) {
        set({ error: errorMessage(err) });
      } finally {
        set({ loading: false });
      }
    },

    stageMove: (keys, target) => {
      const { view, staged } = get();
      const next = { ...staged };
      for (const key of keys) {
        const committed = committedColumnOf(view, key);
        if (committed === target) {
          // Returned to its committed column — drop the staged entry.
          // eslint-disable-next-line @typescript-eslint/no-dynamic-delete -- intentional cache invalidation; key is a chip key string
          delete next[key];
        } else {
          next[key] = target;
        }
      }
      set({ staged: next });
    },

    discard: () => set({ staged: {}, statusMessage: null }),

    effectiveColumnOf: (key) => {
      const { view, staged } = get();
      return staged[key] ?? committedColumnOf(view, key);
    },

    pendingCount: () => Object.keys(get().staged).length,

    apply: async () => {
      const { profile, task, staged } = get();
      const assignments = Object.entries(staged).map(([key, target_split]) => ({
        key,
        target_split,
      }));
      if (assignments.length === 0) return;
      set({ applying: true, error: null, applyErrors: [] });
      try {
        const result = await applyAssignments(profile, task, { assignments });
        const applied = assignments.length - result.errors.length;
        set({
          view: result.view,
          staged: {},
          applyErrors: result.errors,
          statusMessage:
            result.errors.length === 0
              ? `Applied — ${applied} pages committed into '${profile}' / ${task}.`
              : `Applied with ${result.errors.length} error(s); ${applied} pages committed.`,
        });
      } catch (err) {
        set({ error: errorMessage(err) });
        throw err;
      } finally {
        set({ applying: false });
      }
    },

    toggleInclude: async (includeDetection, includeRecognition) => {
      const { profile, task } = get();
      try {
        const view = await setIncludeToggles(
          profile,
          task,
          includeDetection,
          includeRecognition,
        );
        set({ view });
      } catch (err) {
        set({ error: errorMessage(err) });
      }
    },
  }));

export const useDatasetsStore = createDatasetsStore();
