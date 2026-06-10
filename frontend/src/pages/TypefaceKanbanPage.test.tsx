// Tests for TypefaceKanbanPage — M12 typeface-classification kanban wrapper.

import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useDatasetsStore } from "../stores/datasetsStore";
import { TypefaceKanbanPage } from "./TypefaceKanbanPage";

beforeEach(() => {
  vi.unstubAllGlobals();
  // Provide a minimal typeface-classification view so DatasetsPage renders.
  useDatasetsStore.setState({
    profile: "clogaelach",
    task: "typeface-classification",
    view: {
      profile: "clogaelach",
      task: "typeface-classification",
      include_detection: true,
      include_recognition: true,
      columns: {
        unassigned: { rows: [] },
        train: { rows: [] },
        val: { rows: [] },
      },
    },
    staged: {},
    loading: false,
    applying: false,
    error: null,
    applyErrors: [],
    statusMessage: null,
  });
});

describe("TypefaceKanbanPage", () => {
  it("renders with typeface-classification task testid", () => {
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
