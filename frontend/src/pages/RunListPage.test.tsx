// RunListPage tests — run inventory table + driver-contract testids.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { RunListPage } from "./RunListPage";

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: () => Promise.resolve(body),
  } as Response;
}

const run = (id: string, extra: Record<string, unknown> = {}) => ({
  id,
  profile: "clogaelach",
  task: "recognition",
  kind: "train",
  status: "succeeded",
  model_name: `pd-ga-clogaelach-recognition-${id}`,
  args: {},
  notes: null,
  device: null,
  seed: null,
  started_at: "2026-05-21T10:00:00Z",
  finished_at: "2026-05-21T10:05:00Z",
  exit_code: 0,
  artefact_paths: [],
  job_id: "job-1",
  ...extra,
});

describe("RunListPage", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders runs in a table with the driver-contract testids", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, { runs: [run("r1")] }))),
    );
    render(
      <MemoryRouter>
        <RunListPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("run-list-table")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("run-list-row-r1")).toBeInTheDocument();
    expect(screen.getByTestId("run-list-row-r1-status")).toHaveTextContent(
      "succeeded",
    );
    expect(screen.getByTestId("run-list-row-r1-link")).toHaveAttribute(
      "href",
      "/runs/r1",
    );
  });

  it("shows the empty state when there are no runs", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, { runs: [] }))),
    );
    render(
      <MemoryRouter>
        <RunListPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("run-list-empty")).toBeInTheDocument(),
    );
  });

  it("filters runs by status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(200, {
            runs: [run("r1"), run("r2", { status: "failed" })],
          }),
        ),
      ),
    );
    render(
      <MemoryRouter>
        <RunListPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("run-list-row-r1")).toBeInTheDocument(),
    );
    const select = screen.getByTestId("run-list-filter-status") as HTMLSelectElement;
    select.value = "failed";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    await waitFor(() =>
      expect(screen.queryByTestId("run-list-row-r1")).not.toBeInTheDocument(),
    );
    expect(screen.getByTestId("run-list-row-r2")).toBeInTheDocument();
  });
});
