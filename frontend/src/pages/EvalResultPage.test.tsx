// EvalResultPage tests — metrics rendering + driver-contract testids.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { EvalResultPage } from "./EvalResultPage";

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: () => Promise.resolve(body),
  } as Response;
}

const result = (extra: Record<string, unknown> = {}) => ({
  run_id: "eval-1",
  profile: "clogaelach",
  task: "recognition",
  model_name: "pd-ga-clogaelach-recognition-2026-05-05",
  val_source: "local:ml-validation/clogaelach/recognition",
  overall: {
    cer: 0.034,
    wer: 0.092,
    exact_match_rate: null,
    precision: null,
    recall: null,
    f1: null,
    iou_50: null,
    iou_50_95: null,
    accuracy: null,
    f1_macro: null,
    per_class: null,
  },
  slices: [],
  sample_count: 1842,
  excluded_count: 0,
  duration_seconds: 12.3,
  finished_at: "2026-05-21T10:00:00Z",
  ...extra,
});

function renderAt() {
  return render(
    <MemoryRouter initialEntries={["/eval/eval-1/result"]}>
      <Routes>
        <Route path="/eval/:runId/result" element={<EvalResultPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("EvalResultPage", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the overall metrics with the driver-contract testids", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, result()))),
    );
    renderAt();
    await waitFor(() =>
      expect(screen.getByTestId("eval-result-page")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("eval-result-overall-cer")).toHaveTextContent(
      "0.0340",
    );
    expect(screen.getByTestId("eval-result-overall-wer")).toHaveTextContent(
      "0.0920",
    );
    expect(screen.getByTestId("eval-result-download-json")).toBeInTheDocument();
    expect(screen.getByTestId("eval-result-download-md")).toBeInTheDocument();
  });

  it("renders glyph-feature slice rows sorted by |delta_cer|", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(
            200,
            result({
              slices: [
                {
                  feature: "ligature:CT",
                  n_pos: 142,
                  n_neg: 18433,
                  n_excluded: 0,
                  cer_pos: 0.081,
                  cer_neg: 0.034,
                  wer_pos: null,
                  wer_neg: null,
                  delta_cer: 0.047,
                  low_support: false,
                },
                {
                  feature: "long_s",
                  n_pos: 412,
                  n_neg: 18163,
                  n_excluded: 0,
                  cer_pos: 0.142,
                  cer_neg: 0.033,
                  wer_pos: null,
                  wer_neg: null,
                  delta_cer: 0.109,
                  low_support: false,
                },
              ],
            }),
          ),
        ),
      ),
    );
    renderAt();
    await waitFor(() =>
      expect(
        screen.getByTestId("eval-result-slice-long_s"),
      ).toBeInTheDocument(),
    );
    const rows = screen.getAllByTestId(/eval-result-slice-/);
    // long_s has the larger |delta_cer| so it sorts first.
    expect(rows[0]).toHaveAttribute("data-testid", "eval-result-slice-long_s");
  });

  it("shows a pending state when the eval has not finished", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(404, { code: "eval.result_missing", message: "x" }),
        ),
      ),
    );
    renderAt();
    await waitFor(() =>
      expect(screen.getByTestId("eval-result-pending")).toBeInTheDocument(),
    );
  });
});
