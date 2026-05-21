// EvalFormPage tests — eval form + driver-contract testids.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { EvalFormPage } from "./EvalFormPage";

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: () => Promise.resolve(body),
  } as Response;
}

function stubApi() {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.startsWith("/api/profiles")) {
        return Promise.resolve(
          jsonResponse(200, {
            profiles: [
              {
                name: "clogaelach",
                display_name: "Clogaelach",
                language: "ga",
                typeface: "clogaelach",
                is_base: false,
                has_training_data: true,
                has_validation_data: true,
                counts: {},
              },
            ],
          }),
        );
      }
      if (url.startsWith("/api/models")) {
        return Promise.resolve(
          jsonResponse(200, {
            models: [
              {
                model: {
                  name: "pd-ga-clogaelach-recognition-2026-05-05",
                  profile: "clogaelach",
                  task: "recognition",
                  language: "ga",
                  typeface: "clogaelach",
                  paths: { weights: "w", sidecar: "s", config: null },
                  sidecar: {},
                  published_to: [],
                },
                has_sidecar: true,
                is_legacy: false,
              },
            ],
          }),
        );
      }
      return Promise.resolve(jsonResponse(202, { run_id: "r", job_id: "j" }));
    }),
  );
}

describe("EvalFormPage", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the eval form with the driver-contract testids", async () => {
    stubApi();
    render(
      <MemoryRouter>
        <EvalFormPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("eval-form-page")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("eval-form-profile")).toBeInTheDocument();
    expect(screen.getByTestId("eval-form-task-recognition")).toBeInTheDocument();
    expect(screen.getByTestId("eval-form-model")).toBeInTheDocument();
    expect(screen.getByTestId("eval-form-source-local")).toBeInTheDocument();
    expect(screen.getByTestId("eval-form-submit")).toBeInTheDocument();
  });

  it("shows recognition-only checkboxes for the recognition task", async () => {
    stubApi();
    render(
      <MemoryRouter>
        <EvalFormPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(
        screen.getByTestId("eval-form-slice-glyph-features"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("eval-form-persist-predictions"),
    ).toBeInTheDocument();
  });
});
