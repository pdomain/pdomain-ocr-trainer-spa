// ModelsPage tests — model registry table + driver-contract testids.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ModelsPage } from "./ModelsPage";

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: () => Promise.resolve(body),
  } as Response;
}

const modelItem = (name: string, extra: Record<string, unknown> = {}) => ({
  model: {
    name,
    profile: "clogaelach",
    task: "recognition",
    language: "ga",
    typeface: "clogaelach",
    paths: { weights: "w", sidecar: "s", config: null },
    sidecar: {
      name,
      task: "recognition",
      language: "ga",
      typeface: "clogaelach",
      doctr_arch: null,
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

describe("ModelsPage", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders models with the driver-contract testids", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(200, {
            models: [modelItem("pd-ga-clogaelach-recognition-2026-05-05")],
          }),
        ),
      ),
    );
    render(
      <MemoryRouter>
        <ModelsPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("models-table")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("models-row-pd-ga-clogaelach-recognition-2026-05-05"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId(
        "models-row-pd-ga-clogaelach-recognition-2026-05-05-delete",
      ),
    ).toBeInTheDocument();
  });

  it("shows the empty state when there are no models", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, { models: [] }))),
    );
    render(
      <MemoryRouter>
        <ModelsPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("models-empty")).toBeInTheDocument(),
    );
  });

  it("flags a model with a missing sidecar", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(200, {
            models: [
              modelItem("pd-ga-x-recognition-2026", { has_sidecar: false }),
            ],
          }),
        ),
      ),
    );
    render(
      <MemoryRouter>
        <ModelsPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(
        screen.getByTestId(
          "models-row-pd-ga-x-recognition-2026-sidecar-missing",
        ),
      ).toBeInTheDocument(),
    );
  });
});
