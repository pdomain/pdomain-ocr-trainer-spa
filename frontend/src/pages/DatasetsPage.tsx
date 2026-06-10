// DatasetsPage — the 3-column dataset kanban for one (profile, task) pair
// (spec 05). Composes the pdomain-ui KanbanBoard (vendored shim until pdomain-ui ships
// it — see components/kanban/KanbanBoard.tsx) and owns the staged overlay,
// multi-select state, and the keyboard-only flow (spec 12 §3.1 / §9).

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Button, Card } from "@pdomain/pdomain-ui/primitives";
import { KanbanBoard } from "../components/kanban/KanbanBoard";
import type {
  KanbanColumnDef,
  KanbanItemDef,
} from "../components/kanban/KanbanBoard";
import { useDatasetsStore } from "../stores/datasetsStore";
import type { KanbanColumnId, KanbanPageChip } from "../api/datasets";

const COLUMNS: KanbanColumnDef[] = [
  { id: "unassigned", label: "Unassigned" },
  { id: "train", label: "Training" },
  { id: "val", label: "Validation" },
];

interface ChipItem extends KanbanItemDef {
  chip: KanbanPageChip;
  projectId: string;
}

function chipTestId(item: ChipItem): string {
  // spec 13 §4.3 — kanban-column-{column}-chip-{project}-{name}
  return `kanban-column-${item.columnId}-chip-${item.projectId}-${item.chip.crop_name ?? item.chip.page_name}`;
}

interface DatasetsPageProps {
  /** Override the task instead of reading :task from the URL.
   *
   * Use this when the route does not capture a `:task` param — e.g. the
   * typeface-classification route `/profiles/:name/datasets/typeface-classification`
   * has a literal segment rather than a dynamic param.  Without this prop,
   * `params.task` would be `undefined` and the page would silently default to
   * `"recognition"` (see M12 bug fix).
   */
  overrideTask?: string;
}

export function DatasetsPage({
  overrideTask,
}: DatasetsPageProps = {}): React.JSX.Element {
  const params = useParams<{ name: string; task: string }>();
  const profile = params.name ?? "all";
  const task = overrideTask ?? params.task ?? "recognition";

  const view = useDatasetsStore((s) => s.view);
  const loading = useDatasetsStore((s) => s.loading);
  const applying = useDatasetsStore((s) => s.applying);
  const error = useDatasetsStore((s) => s.error);
  const applyErrors = useDatasetsStore((s) => s.applyErrors);
  const statusMessage = useDatasetsStore((s) => s.statusMessage);
  const staged = useDatasetsStore((s) => s.staged);
  const load = useDatasetsStore((s) => s.load);
  const rescan = useDatasetsStore((s) => s.rescan);
  const stageMove = useDatasetsStore((s) => s.stageMove);
  const discard = useDatasetsStore((s) => s.discard);
  const apply = useDatasetsStore((s) => s.apply);
  const toggleInclude = useDatasetsStore((s) => s.toggleInclude);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState("");

  useEffect(() => {
    void load(profile, task);
  }, [load, profile, task]);

  const pendingIds = useMemo(() => new Set(Object.keys(staged)), [staged]);
  const pendingCount = pendingIds.size;

  // Build the effective items map: every chip placed in its staged-or-committed
  // column, then substring-filtered by project id.
  const items = useMemo(() => {
    const map = new Map<string, ChipItem[]>([
      ["unassigned", []],
      ["train", []],
      ["val", []],
    ]);
    if (!view) return map;
    const lcFilter = filter.trim().toLowerCase();
    for (const columnId of ["unassigned", "train", "val"] as KanbanColumnId[]) {
      for (const row of view.columns[columnId].rows) {
        if (lcFilter && !row.project_id.toLowerCase().includes(lcFilter)) {
          continue;
        }
        for (const chip of row.pages) {
          const effective = (staged[chip.key] ?? columnId) as KanbanColumnId;
          map.get(effective)?.push({
            id: chip.key,
            columnId: effective,
            chip,
            projectId: row.project_id,
          });
        }
      }
    }
    return map;
  }, [view, staged, filter]);

  const totalChips = useMemo(() => {
    if (!view) return 0;
    let n = 0;
    for (const columnId of ["unassigned", "train", "val"] as KanbanColumnId[]) {
      for (const row of view.columns[columnId].rows) n += row.pages.length;
    }
    return n;
  }, [view]);

  const shownChips = useMemo(
    () =>
      [...items.values()].reduce(
        (sum, columnItems) => sum + columnItems.length,
        0,
      ),
    [items],
  );

  const moveSelected = useCallback(
    (target: KanbanColumnId) => {
      const keys = selectedIds.size > 0 ? [...selectedIds] : [];
      if (keys.length === 0) return;
      stageMove(keys, target);
    },
    [selectedIds, stageMove],
  );

  // Page-scoped hotkeys (spec 12 §3.1, scope `kanban`).
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      switch (e.key) {
        case "r":
          e.preventDefault();
          void rescan();
          break;
        case "a":
          e.preventDefault();
          if (pendingCount > 0) void apply();
          break;
        case "d":
          e.preventDefault();
          discard();
          break;
        case "t":
          e.preventDefault();
          moveSelected("train");
          break;
        case "v":
          e.preventDefault();
          moveSelected("val");
          break;
        case "u":
          e.preventDefault();
          moveSelected("unassigned");
          break;
        case "Escape":
          setSelectedIds(new Set());
          break;
        default:
          break;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [rescan, apply, discard, moveSelected, pendingCount]);

  const handleSelect = useCallback(
    ({ itemId, extend }: { itemId: string; extend: boolean }) => {
      setSelectedIds((prev) => {
        const next = new Set(extend ? prev : []);
        if (extend && prev.has(itemId)) next.delete(itemId);
        else next.add(itemId);
        return next;
      });
    },
    [],
  );

  return (
    <div data-testid="kanban-page">
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <h1 tabIndex={-1}>
          Datasets — {profile} / {task}
        </h1>
      </header>

      {error && (
        <p data-testid="kanban-error" role="alert">
          {error}
        </p>
      )}
      {applyErrors.length > 0 && (
        <p data-testid="kanban-apply-errors" role="alert">
          {applyErrors.length} item(s) failed to apply:{" "}
          {applyErrors.map((e) => e.key).join(", ")}
        </p>
      )}

      <div
        data-testid="kanban-toolbar"
        style={{ display: "flex", gap: "1rem", alignItems: "center" }}
      >
        <Button
          data-testid="kanban-toolbar-rescan"
          variant="ghost"
          onClick={() => void rescan()}
        >
          Rescan
        </Button>
        <label>
          <input
            data-testid="kanban-toolbar-include-detection"
            type="checkbox"
            checked={view?.include_detection ?? true}
            onChange={(e) =>
              void toggleInclude(
                e.target.checked,
                view?.include_recognition ?? true,
              )
            }
          />
          Include detection
        </label>
        <label>
          <input
            data-testid="kanban-toolbar-include-recognition"
            type="checkbox"
            checked={view?.include_recognition ?? true}
            onChange={(e) =>
              void toggleInclude(
                view?.include_detection ?? true,
                e.target.checked,
              )
            }
          />
          Include recognition
        </label>
        <input
          data-testid="kanban-toolbar-filter-input"
          type="text"
          placeholder="Filter projects…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <span data-testid="kanban-toolbar-count">
          Showing {shownChips} of {totalChips} pages
        </span>
      </div>

      {loading && <p data-testid="kanban-loading">Loading…</p>}

      <Card>
        <KanbanBoard<KanbanColumnDef, ChipItem>
          columns={COLUMNS}
          items={items}
          selectedIds={selectedIds}
          pendingIds={pendingIds}
          chipTestId={chipTestId}
          onSelect={handleSelect}
          onMove={({ itemIds, toColumnId }) =>
            stageMove(itemIds, toColumnId as KanbanColumnId)
          }
          renderColumnHeader={({ column, itemCount }) => (
            <h2 data-testid={`kanban-column-${column.id}-header`}>
              {column.label} ({itemCount})
            </h2>
          )}
          renderChip={({ item, isPending }) => (
            <span
              title={item.chip.change_summary ?? undefined}
              style={{
                background: item.chip.is_changed
                  ? "var(--warning-surface, #fef9c3)"
                  : undefined,
                fontWeight: isPending ? 600 : undefined,
              }}
            >
              {item.chip.label_text ?? item.chip.page_name}
              {item.chip.is_changed ? " ⚠" : ""}
            </span>
          )}
        />
      </Card>

      <footer
        data-testid="kanban-footer"
        style={{ display: "flex", gap: "1rem", alignItems: "center" }}
      >
        <span data-testid="kanban-footer-pending-count">
          {pendingCount > 0
            ? `${pendingCount} pending moves`
            : "No pending changes"}
        </span>
        <Button
          data-testid="kanban-footer-discard"
          variant="ghost"
          disabled={pendingCount === 0}
          onClick={() => discard()}
        >
          Discard
        </Button>
        <Button
          data-testid="kanban-footer-apply"
          disabled={pendingCount === 0 || applying}
          onClick={() => void apply()}
        >
          {applying ? "Applying…" : "Apply"}
        </Button>
        {statusMessage && (
          <span data-testid="kanban-footer-status">{statusMessage}</span>
        )}
      </footer>
    </div>
  );
}
