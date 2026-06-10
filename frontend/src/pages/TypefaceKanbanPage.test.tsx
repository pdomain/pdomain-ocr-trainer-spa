// Tests for TypefaceKanbanPage — M12 typeface-classification kanban wrapper.
//
// The key invariant: TypefaceKanbanPage must request typeface-classification
// data, NOT recognition data.  The old test masked the routing bug by
// pre-injecting store state with task="typeface-classification"; now the test
// renders via MemoryRouter at the typeface URL with NO store pre-injection
// and asserts the kanban fetch is for typeface-classification.
//
// Mechanism: DatasetsPage.load() calls fetchKanban(profile, task) which hits
// /api/profiles/{profile}/datasets/{task}/kanban.  We intercept global fetch
// and inspect the URL that was requested.

import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TypefaceKanbanPage } from "./TypefaceKanbanPage";

// Minimal KanbanView shape that DatasetsPage can render without crashing.
function emptyView(task: string) {
  return {
    profile: "clogaelach",
    task,
    include_detection: true,
    include_recognition: true,
    columns: {
      unassigned: { rows: [] },
      train: { rows: [] },
      val: { rows: [] },
    },
  };
}

beforeEach(() => {
  vi.unstubAllGlobals();
  // Do NOT pre-inject store state — the bug was that pre-injection hid the
  // routing defect.  We let the component call load() naturally and intercept
  // the resulting fetch.
});

describe("TypefaceKanbanPage routing fix (M12 issue 1)", () => {
  it("fetches typeface-classification data, NOT recognition", async () => {
    const fetchMock = vi.fn((url: unknown) => {
      const task = String(url).includes("typeface-classification")
        ? "typeface-classification"
        : "recognition";
      return Promise.resolve({
        ok: true,
        status: 200,
        statusText: "",
        json: () => Promise.resolve(emptyView(task)),
        headers: { get: () => null },
      } as unknown as Response);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter
        initialEntries={[
          "/profiles/clogaelach/datasets/typeface-classification",
        ]}
      >
        <Routes>
          <Route
            path="/profiles/:name/datasets/typeface-classification"
            element={<TypefaceKanbanPage />}
          />
        </Routes>
      </MemoryRouter>,
    );

    // testid wrapper must appear
    expect(screen.getByTestId("typeface-kanban-page")).toBeInTheDocument();

    // The store's load() must have been called with typeface-classification.
    // It fires fetch to /api/profiles/{profile}/datasets/{task}/kanban.
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const calledUrls: string[] = fetchMock.mock.calls.map(([u]: unknown[]) =>
      String(u),
    );
    const typefaceCall = calledUrls.some((u) =>
      u.includes("typeface-classification"),
    );
    const recognitionCall = calledUrls.some((u) =>
      u.includes("/datasets/recognition"),
    );

    expect(typefaceCall).toBe(true);
    expect(recognitionCall).toBe(false);
  });

  it("renders typeface-kanban-page testid", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          statusText: "",
          json: () => Promise.resolve(emptyView("typeface-classification")),
          headers: { get: () => null },
        } as unknown as Response),
      ),
    );

    render(
      <MemoryRouter
        initialEntries={[
          "/profiles/clogaelach/datasets/typeface-classification",
        ]}
      >
        <Routes>
          <Route
            path="/profiles/:name/datasets/typeface-classification"
            element={<TypefaceKanbanPage />}
          />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("typeface-kanban-page")).toBeInTheDocument();
  });
});
