// RunDetailPage tests — run monitor: status, progress, cancel, chart, log.
// Exercises acceptance scenarios 2-6 (specs/06 §10) at the UI layer.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { RunDetailPage } from "./RunDetailPage";

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: () => Promise.resolve(body),
  } as Response;
}

const run = (extra: Record<string, unknown> = {}) => ({
  id: "r1",
  profile: "clogaelach",
  task: "recognition",
  kind: "train",
  status: "succeeded",
  model_name: "pd-ga-clogaelach-recognition-2026-05-21",
  args: { epochs: 5 },
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

function routeFor(): JSX.Element {
  return (
    <MemoryRouter initialEntries={["/runs/r1"]}>
      <Routes>
        <Route path="/runs/:runId" element={<RunDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
}

class NoopEventSource {
  close() {}
  addEventListener() {}
  onerror: ((e: Event) => void) | null = null;
}

describe("RunDetailPage", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.stubGlobal("EventSource", NoopEventSource);
  });

  function fetchFor(runBody: unknown, progressRecords: unknown[]) {
    return vi.fn((url: string) => {
      if (String(url).endsWith("/progress")) {
        return Promise.resolve(jsonResponse(200, { records: progressRecords }));
      }
      return Promise.resolve(jsonResponse(200, runBody));
    });
  }

  it("renders the run-detail page with status badge + args summary", async () => {
    vi.stubGlobal("fetch", fetchFor(run(), []));
    render(routeFor());
    await waitFor(
      () => expect(screen.getByTestId("run-detail-page")).toBeInTheDocument(),
      { timeout: 5000 },
    );
    expect(screen.getByTestId("run-detail-status-badge")).toHaveTextContent(
      "succeeded",
    );
    expect(screen.getByTestId("run-detail-args-summary")).toHaveTextContent(
      "epochs",
    );
    expect(screen.getByTestId("run-detail-loss-chart")).toBeInTheDocument();
    expect(screen.getByTestId("run-detail-log-viewer")).toBeInTheDocument();
  });

  it("replays metric points from progress.jsonl onto the loss chart", async () => {
    vi.stubGlobal(
      "fetch",
      fetchFor(run(), [
        { t: 1, type: "metric", value: 0.2 },
        { t: 2, type: "metric", value: 0.05 },
      ]),
    );
    render(routeFor());
    await waitFor(
      () => expect(screen.getByText(/latest 0.0500/)).toBeInTheDocument(),
      { timeout: 5000 },
    );
  });

  it("shows Cancel only for a running run and posts on click", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (String(url).endsWith("/cancel")) {
        return Promise.resolve(
          jsonResponse(202, run({ status: "cancelled" })),
        );
      }
      if (String(url).endsWith("/progress")) {
        return Promise.resolve(jsonResponse(200, { records: [] }));
      }
      return Promise.resolve(jsonResponse(200, run({ status: "running" })));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(routeFor());
    await waitFor(
      () => expect(screen.getByTestId("run-detail-cancel")).toBeInTheDocument(),
      { timeout: 5000 },
    );
    await userEvent.click(screen.getByTestId("run-detail-cancel"));
    await waitFor(() =>
      expect(screen.getByTestId("run-detail-status-badge")).toHaveTextContent(
        "cancelled",
      ),
    );
  });

  it("shows Open Model only on a succeeded run", async () => {
    vi.stubGlobal("fetch", fetchFor(run({ status: "succeeded" }), []));
    render(routeFor());
    await waitFor(
      () => expect(screen.getByTestId("run-detail-open-model")).toBeInTheDocument(),
      { timeout: 5000 },
    );
    expect(screen.queryByTestId("run-detail-cancel")).not.toBeInTheDocument();
  });
});
