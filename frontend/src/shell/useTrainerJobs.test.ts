/**
 * Producer-consumer contract tests for useTrainerJobs.
 *
 * The fixture payloads below are copied verbatim from the backend integration
 * test `tests/integration/api/test_jobs.py::test_list_jobs_returns_job_shape`.
 * If a backend field is renamed, BOTH test files must change together — that is
 * the point.  The field names here MUST match the serialized Job model in
 * src/pdomain_ocr_trainer_spa/core/models.py (Job.progress, not "pct").
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import { useTrainerJobs } from "./useTrainerJobs";

/**
 * Backend-canonical per-job shape (mirrors Job model serialized by _project()
 * in api/jobs.py).  Copied from test_list_jobs_returns_job_shape assertion keys.
 *
 * NOTE: "progress" is the canonical field name — NOT "pct".
 */
type BackendJob = {
  id: string;
  run_id: string | null;
  kind: string;
  state: string;
  progress: number; // 0.0–1.0 — the backend serializes this as "progress"
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
};

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children);
}

/** Backend-shaped fixture payloads (field names from test_list_jobs_returns_job_shape). */
const BACKEND_JOBS: BackendJob[] = [
  {
    id: "job-1",
    run_id: null,
    kind: "train.recognition",
    state: "running",
    progress: 0.42, // backend sends 0.0–1.0 float, not pct
    error: null,
    started_at: "2026-06-10T12:00:00Z",
    finished_at: null,
  },
  {
    id: "job-2",
    run_id: null,
    kind: "train.detection",
    state: "succeeded",
    progress: 1.0,
    error: null,
    started_at: "2026-06-10T11:00:00Z",
    finished_at: "2026-06-10T11:30:00Z",
  },
  {
    id: "job-3",
    run_id: null,
    kind: "train.recognition",
    state: "cancelled",
    progress: 0.0,
    error: "cancelled by user",
    started_at: "2026-06-10T10:00:00Z",
    finished_at: "2026-06-10T10:05:00Z",
  },
];

describe("useTrainerJobs", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(BACKEND_JOBS),
        } as Response),
      ),
    );
  });
  afterEach(() => vi.unstubAllGlobals());

  it("returns pill for in-flight jobs only", async () => {
    const { result } = renderHook(() => useTrainerJobs(), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(result.current.pill.length).toBe(1));
    expect(result.current.pill[0].id).toBe("job-1");
  });

  it("maps backend progress (0.0-1.0) correctly — not pct", async () => {
    const { result } = renderHook(() => useTrainerJobs(), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(result.current.pill.length).toBe(1));
    // job-1 has progress: 0.42 — hook must pass it through, not read "pct"
    expect(result.current.pill[0].pct).toBe(0.42);
  });

  it("returns all jobs in dock array", async () => {
    const { result } = renderHook(() => useTrainerJobs(), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(result.current.dock.length).toBe(3));
  });

  it("maps cancelled state to failed for dock", async () => {
    const { result } = renderHook(() => useTrainerJobs(), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(result.current.dock.length).toBe(3));
    const cancelled = result.current.dock.find((j) => j.id === "job-3");
    expect(cancelled?.status).toBe("failed");
  });

  it("silent empty-list fallback on non-ok response — no error thrown", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 404,
          json: () => Promise.resolve({}),
        } as Response),
      ),
    );
    const { result } = renderHook(() => useTrainerJobs(), {
      wrapper: makeWrapper(),
    });
    // After the fetch resolves, dock/pill should both be empty — not an error
    await waitFor(() => expect(result.current.dock).toEqual([]));
    expect(result.current.pill).toEqual([]);
  });
});
