// VENDORED pdomain-ui KanbanBoard — TEMPORARY SHIM.
//
// D-T4 designates the dataset kanban (KanbanBoard / KanbanColumn / PageChip)
// as a `pdomain-ui` component imported from `@pdomain/pdomain-ui/primitives`.
// As of `@pdomain/pdomain-ui@0.1.0-alpha` that component is NOT published
// (the pdomain-ui kanban-board spec, `pdomain-ui/docs/specs/2026-05-21-kanban-board.md`,
// is still "Status: Spec — not yet implemented", blocked on `@dnd-kit` being
// added to pdomain-ui's package.json).
//
// To unblock M4 this module implements the spec'd KanbanBoard *prop contract*
// verbatim (KanbanColumnDef / KanbanItemDef / KanbanMoveEvent / KanbanSelectEvent,
// renderColumnHeader / renderChip render-props, selectedIds / onSelect / onMove).
// Pointer DnD is replaced by an accessible keyboard grab/move/drop flow
// (Space grab, arrows, Space drop, Esc abort) — see spec 12 §9 scenario 3.
//
// REMOVE this file and switch the import to
//   `import { KanbanBoard } from "@pdomain/pdomain-ui/primitives";`
// once pdomain-ui publishes the real component. See the M4 cross-repo recommendation.

import { useCallback, useRef, useState } from "react";

export interface KanbanColumnDef {
  id: string;
  label: string;
}

export interface KanbanItemDef {
  id: string;
  columnId: string;
}

export interface KanbanMoveEvent<
  TColumnId extends string,
  TItemId extends string,
> {
  itemIds: TItemId[];
  fromColumnId: TColumnId | null;
  toColumnId: TColumnId;
  via: "pointer" | "keyboard";
}

export interface KanbanSelectEvent<TItemId extends string> {
  itemId: TItemId;
  extend: boolean;
}

export interface KanbanColumnHeaderProps<TColumn extends KanbanColumnDef> {
  column: TColumn;
  itemCount: number;
}

export interface KanbanChipRenderProps<TItem extends KanbanItemDef> {
  item: TItem;
  isSelected: boolean;
  isPending: boolean;
}

export interface KanbanBoardProps<
  TColumn extends KanbanColumnDef,
  TItem extends KanbanItemDef,
> {
  columns: TColumn[];
  items: Map<TColumn["id"], TItem[]>;
  onMove: (event: KanbanMoveEvent<TColumn["id"], TItem["id"]>) => void;
  renderColumnHeader: (
    props: KanbanColumnHeaderProps<TColumn>,
  ) => React.ReactNode;
  renderChip: (props: KanbanChipRenderProps<TItem>) => React.ReactNode;
  selectedIds?: ReadonlySet<TItem["id"]>;
  onSelect?: (event: KanbanSelectEvent<TItem["id"]>) => void;
  /** Set of item ids with a staged (uncommitted) move. */
  pendingIds?: ReadonlySet<TItem["id"]>;
  /** Render-prop for a chip's data-testid. */
  chipTestId?: (item: TItem) => string;
  className?: string;
}

interface GrabState<TItemId extends string, TColumnId extends string> {
  itemIds: TItemId[];
  fromColumnId: TColumnId;
  targetColumnId: TColumnId;
}

export function KanbanBoard<
  TColumn extends KanbanColumnDef,
  TItem extends KanbanItemDef,
>({
  columns,
  items,
  onMove,
  renderColumnHeader,
  renderChip,
  selectedIds,
  onSelect,
  pendingIds,
  chipTestId,
  className,
}: KanbanBoardProps<TColumn, TItem>) {
  const [grab, setGrab] = useState<GrabState<
    TItem["id"],
    TColumn["id"]
  > | null>(null);
  const boardRef = useRef<HTMLDivElement>(null);

  const columnIndexOf = useCallback(
    (id: string) => columns.findIndex((c) => c.id === id),
    [columns],
  );

  const handleChipKeyDown = useCallback(
    (event: React.KeyboardEvent, item: TItem) => {
      const key = event.key;
      if (key === " " || key === "Spacebar") {
        event.preventDefault();
        if (!grab) {
          // Grab — pick up this chip (plus any selected siblings).
          const ids =
            selectedIds && selectedIds.has(item.id)
              ? [...selectedIds]
              : [item.id];
          setGrab({
            itemIds: ids as TItem["id"][],
            fromColumnId: item.columnId as TColumn["id"],
            targetColumnId: item.columnId as TColumn["id"],
          });
        } else {
          // Drop — commit the move into the ghost's target column.
          if (grab.targetColumnId !== grab.fromColumnId) {
            onMove({
              itemIds: grab.itemIds,
              fromColumnId: grab.fromColumnId,
              toColumnId: grab.targetColumnId,
              via: "keyboard",
            });
          }
          setGrab(null);
        }
        return;
      }
      if (grab && (key === "ArrowLeft" || key === "ArrowRight")) {
        event.preventDefault();
        const delta = key === "ArrowRight" ? 1 : -1;
        const current = columnIndexOf(grab.targetColumnId);
        const next = Math.min(columns.length - 1, Math.max(0, current + delta));
        setGrab({ ...grab, targetColumnId: columns[next].id as TColumn["id"] });
        return;
      }
      if (key === "Escape") {
        if (grab) {
          event.preventDefault();
          setGrab(null);
        }
        return;
      }
      if (key === "x" || key === "X") {
        event.preventDefault();
        onSelect?.({ itemId: item.id, extend: false });
      }
    },
    [grab, selectedIds, onMove, onSelect, columns, columnIndexOf],
  );

  return (
    <div
      ref={boardRef}
      className={className}
      data-testid="kanban-board"
      style={{ display: "flex", gap: "1rem", alignItems: "flex-start" }}
    >
      {columns.map((column) => {
        const columnItems = items.get(column.id) ?? [];
        const isGrabTarget = grab?.targetColumnId === column.id;
        return (
          <section
            key={column.id}
            data-testid={`kanban-column-${column.id}`}
            role="region"
            aria-label={column.label}
            aria-keyshortcuts="j k h l"
            data-grab-target={isGrabTarget ? "true" : undefined}
            style={{
              flex: 1,
              minWidth: 0,
              outline: isGrabTarget
                ? "2px solid var(--accent, #3b82f6)"
                : undefined,
            }}
          >
            {renderColumnHeader({ column, itemCount: columnItems.length })}
            <ul
              role="list"
              data-testid={`kanban-column-${column.id}-list`}
              style={{ listStyle: "none", margin: 0, padding: 0 }}
            >
              {columnItems.map((item) => {
                const isSelected = selectedIds?.has(item.id) ?? false;
                const isPending = pendingIds?.has(item.id) ?? false;
                const isGrabbed = grab?.itemIds.includes(item.id) ?? false;
                return (
                  <li
                    key={item.id}
                    role="listitem"
                    tabIndex={0}
                    aria-grabbed={isGrabbed}
                    data-testid={chipTestId?.(item)}
                    data-pending={isPending ? "true" : undefined}
                    data-selected={isSelected ? "true" : undefined}
                    onKeyDown={(e) => handleChipKeyDown(e, item)}
                    onClick={(e) =>
                      onSelect?.({ itemId: item.id, extend: e.shiftKey })
                    }
                    style={{
                      outline: isSelected
                        ? "2px solid var(--accent, #3b82f6)"
                        : isGrabbed
                          ? "2px dashed var(--accent, #3b82f6)"
                          : undefined,
                      cursor: "pointer",
                    }}
                  >
                    {renderChip({ item, isSelected, isPending })}
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
