// DatasetsPage tests — kanban acceptance scenarios (spec 05 §11, recognition
// only) plus the keyboard-only flow (spec 12 §9 scenario 3) and the
// driver-contract testids (spec 13 §4.3).

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { DatasetsPage } from "./DatasetsPage";
import { useDatasetsStore } from "../stores/datasetsStore";
import type { KanbanView } from "../api/datasets";

function jsonResponse(
  status: number,
  body: unknown,
  headers: Record<string, string> = {},
): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: () => Promise.resolve(body),
    headers: { get: (k: string) => headers[k] ?? null },
  } as unknown as Response;
}

function chip(key: string, label: string, isChanged = false) {
  return {
    key,
    page_name: key.split(":")[1],
    crop_name: key.split(":")[1],
    label_text: label,
    is_changed: isChanged,
    change_summary: isChanged ? "label changed: 'old' -> 'new'" : null,
  };
}

function view(): KanbanView {
  return {
    profile: "all",
    task: "recognition",
    include_detection: true,
    include_recognition: true,
    columns: {
      unassigned: {
        rows: [
          {
            project_id: "myproj",
            source: "pending",
            page_count: 1,
            is_changed: false,
            style_tags: [],
            pages: [chip("myproj:myproj_1_0.png", "hello")],
          },
        ],
      },
      train: { rows: [] },
      val: { rows: [] },
    },
  };
}

function appliedView(): KanbanView {
  const v = view();
  return {
    ...v,
    columns: {
      unassigned: { rows: [] },
      train: {
        rows: [{ ...v.columns.unassigned.rows[0], source: "on_disk" }],
      },
      val: { rows: [] },
    },
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/profiles/all/datasets/recognition"]}>
      <Routes>
        <Route
          path="/profiles/:name/datasets/:task"
          element={<DatasetsPage />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.unstubAllGlobals();
  useDatasetsStore.setState({
    profile: "",
    task: "recognition",
    view: null,
    staged: {},
    loading: false,
    applying: false,
    error: null,
    applyErrors: [],
    statusMessage: null,
  });
});

describe("DatasetsPage — kanban acceptance (spec 05 §11)", () => {
  it("scenario 1: an export appears in the Unassigned column", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, view()))),
    );
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId("kanban-page")).toBeInTheDocument(),
    );
    const unassigned = screen.getByTestId("kanban-column-unassigned");
    expect(
      within(unassigned).getByTestId(
        "kanban-column-unassigned-chip-myproj-myproj_1_0.png",
      ),
    ).toBeInTheDocument();
  });

  it("scenario 2 & 3: drag stages a move, footer counts it, Apply commits", async () => {
    const fetchMock = vi.fn((url: string) =>
      Promise.resolve(
        jsonResponse(
          200,
          String(url).endsWith("/apply") ? appliedView() : view(),
        ),
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId("kanban-page")).toBeInTheDocument(),
    );

    // Select the chip, stage it into Training via the `t` hotkey.
    await user.click(
      screen.getByTestId("kanban-column-unassigned-chip-myproj-myproj_1_0.png"),
    );
    await user.keyboard("t");

    // Footer reflects the pending move; no apply request fired yet.
    expect(screen.getByTestId("kanban-footer-pending-count")).toHaveTextContent(
      "1 pending moves",
    );
    expect(
      fetchMock.mock.calls.some(([u]) => String(u).endsWith("/apply")),
    ).toBe(false);

    // Apply commits — chip lands under train, footer clears.
    await user.click(screen.getByTestId("kanban-footer-apply"));
    await waitFor(() =>
      expect(
        screen.getByTestId("kanban-footer-pending-count"),
      ).toHaveTextContent("No pending changes"),
    );
    const train = screen.getByTestId("kanban-column-train");
    expect(
      within(train).getByTestId(
        "kanban-column-train-chip-myproj-myproj_1_0.png",
      ),
    ).toBeInTheDocument();
  });

  it("scenario 6: Discard reverts the staged overlay with no request", async () => {
    const fetchMock = vi.fn(() => Promise.resolve(jsonResponse(200, view())));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId("kanban-page")).toBeInTheDocument(),
    );
    await user.click(
      screen.getByTestId("kanban-column-unassigned-chip-myproj-myproj_1_0.png"),
    );
    await user.keyboard("t");
    expect(screen.getByTestId("kanban-footer-pending-count")).toHaveTextContent(
      "1 pending moves",
    );
    await user.click(screen.getByTestId("kanban-footer-discard"));
    expect(screen.getByTestId("kanban-footer-pending-count")).toHaveTextContent(
      "No pending changes",
    );
    expect(
      fetchMock.mock.calls.some(([u]) => String(u).endsWith("/apply")),
    ).toBe(false);
  });
});

describe("DatasetsPage — keyboard-only flow (spec 12 §9 scenario 3)", () => {
  it("Space grabs a chip, arrows move the ghost, Space drops it staged", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, view()))),
    );
    const user = userEvent.setup();
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId("kanban-page")).toBeInTheDocument(),
    );

    const chipEl = screen.getByTestId(
      "kanban-column-unassigned-chip-myproj-myproj_1_0.png",
    );
    chipEl.focus();
    // Space → grab (data-grabbed flips true; aria-grabbed is deprecated in ARIA 1.2).
    await user.keyboard(" ");
    expect(chipEl).toHaveAttribute("data-grabbed", "true");
    // ArrowRight → ghost target moves to Training.
    await user.keyboard("{ArrowRight}");
    expect(screen.getByTestId("kanban-column-train")).toHaveAttribute(
      "data-grab-target",
      "true",
    );
    // Space → drop; the move is staged client-side (no request).
    await user.keyboard(" ");
    expect(screen.getByTestId("kanban-footer-pending-count")).toHaveTextContent(
      "1 pending moves",
    );
  });

  it("Esc aborts an in-progress keyboard grab", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, view()))),
    );
    const user = userEvent.setup();
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId("kanban-page")).toBeInTheDocument(),
    );
    const chipEl = screen.getByTestId(
      "kanban-column-unassigned-chip-myproj-myproj_1_0.png",
    );
    chipEl.focus();
    await user.keyboard(" ");
    await user.keyboard("{ArrowRight}");
    await user.keyboard("{Escape}");
    expect(chipEl).not.toHaveAttribute("data-grabbed");
    expect(screen.getByTestId("kanban-footer-pending-count")).toHaveTextContent(
      "No pending changes",
    );
  });
});

describe("DatasetsPage — toolbar", () => {
  it("the changed highlight marks a changed chip", async () => {
    const changed = view();
    changed.columns.unassigned.rows[0].pages[0] = chip(
      "myproj:myproj_1_0.png",
      "new",
      true,
    );
    changed.columns.unassigned.rows[0].is_changed = true;
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, changed))),
    );
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId("kanban-page")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("kanban-column-unassigned-chip-myproj-myproj_1_0.png"),
    ).toHaveTextContent("⚠");
  });

  it("the project filter narrows the shown count", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, view()))),
    );
    const user = userEvent.setup();
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId("kanban-page")).toBeInTheDocument(),
    );
    await user.type(
      screen.getByTestId("kanban-toolbar-filter-input"),
      "nomatch",
    );
    expect(screen.getByTestId("kanban-toolbar-count")).toHaveTextContent(
      "Showing 0 of 1 pages",
    );
  });
});
