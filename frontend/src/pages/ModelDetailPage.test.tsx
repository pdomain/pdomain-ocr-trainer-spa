// ModelDetailPage tests — sidecar viewer + rename + regenerate testids.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ModelDetailPage } from "./ModelDetailPage";

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: () => Promise.resolve(body),
  } as Response;
}

const NAME = "pd-ga-clogaelach-recognition-2026-05-05";

const item = (extra: Record<string, unknown> = {}) => ({
  model: {
    name: NAME,
    profile: "clogaelach",
    task: "recognition",
    language: "ga",
    typeface: "clogaelach",
    paths: { weights: "w", sidecar: "s", config: null },
    sidecar: {
      name: NAME,
      task: "recognition",
      language: "ga",
      typeface: "clogaelach",
      doctr_arch: "crnn_vgg16_bn",
      trainer_version: null,
      trained_at: null,
      trained_on: [],
      args: {},
      qualifier: null,
      eval: null,
    },
    published_to: [],
  },
  has_sidecar: true,
  is_legacy: false,
  ...extra,
});

function renderAt(name: string) {
  return render(
    <MemoryRouter initialEntries={[`/models/${name}`]}>
      <Routes>
        <Route path="/models/:name" element={<ModelDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ModelDetailPage", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the sidecar JSON viewer and action buttons", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, item()))),
    );
    renderAt(NAME);
    await waitFor(() =>
      expect(screen.getByTestId("models-detail-page")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("models-detail-sidecar-json")).toHaveTextContent(
      "crnn_vgg16_bn",
    );
    expect(screen.getByTestId("models-detail-rename")).toBeInTheDocument();
    expect(screen.getByTestId("models-detail-open-eval")).toHaveAttribute(
      "href",
      `/eval?model=${encodeURIComponent(NAME)}`,
    );
  });

  it("offers regeneration when the sidecar is missing", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(jsonResponse(200, item({ has_sidecar: false }))),
      ),
    );
    renderAt(NAME);
    await waitFor(() =>
      expect(
        screen.getByTestId("models-detail-regenerate"),
      ).toBeInTheDocument(),
    );
  });
});
