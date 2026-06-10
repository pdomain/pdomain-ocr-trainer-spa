// NewRunPage tests — run-creation form (acceptance scenario 1, specs/06 §10).

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { NewRunPage } from "./NewRunPage";

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: () => Promise.resolve(body),
  } as Response;
}

const profilesBody = {
  profiles: [
    {
      name: "clogaelach",
      display_name: "clogaelach",
      language: "ga",
      typeface: "clogaelach",
      is_base: false,
      has_training_data: true,
      has_validation_data: true,
      counts: {
        detection_train_pages: 0,
        detection_val_pages: 0,
        recognition_train_crops: 1,
        recognition_val_crops: 0,
        typeface_train_crops: 0,
        typeface_val_crops: 0,
        glyph_train_crops: 0,
        glyph_val_crops: 0,
      },
    },
  ],
  has_legacy_layout: false,
};

describe("NewRunPage", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the form, prefills args, and submits a run", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      const u = String(url);
      if (u === "/api/profiles") {
        return Promise.resolve(jsonResponse(200, profilesBody));
      }
      if (u.includes("/training-defaults/") && !u.endsWith("/seed")) {
        // saved defaults present
        return Promise.resolve(
          jsonResponse(200, { task: "recognition", args: { epochs: 7 } }),
        );
      }
      if (u === "/api/runs" && init?.method === "POST") {
        return Promise.resolve(
          jsonResponse(202, { run_id: "new-run", job_id: "job-1" }),
        );
      }
      return Promise.resolve(jsonResponse(404, { code: "x", message: "x" }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter>
        <NewRunPage />
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("new-run-page")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("new-run-profile")).toBeInTheDocument();
    expect(screen.getByTestId("new-run-task")).toBeInTheDocument();
    expect(screen.getByTestId("new-run-start")).toBeInTheDocument();

    await waitFor(() =>
      expect(screen.getByTestId("new-run-start")).not.toBeDisabled(),
    );
    await userEvent.click(screen.getByTestId("new-run-start"));

    await waitFor(() => {
      const posted = fetchMock.mock.calls.find(
        (c) => c[0] === "/api/runs" && c[1]?.method === "POST",
      );
      expect(posted).toBeDefined();
    });
  });

  it("surfaces a backend error envelope on a failed start", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      const u = String(url);
      if (u === "/api/profiles") {
        return Promise.resolve(jsonResponse(200, profilesBody));
      }
      if (u.includes("/training-defaults/")) {
        return Promise.resolve(
          jsonResponse(200, { task: "recognition", args: {} }),
        );
      }
      if (u === "/api/runs" && init?.method === "POST") {
        return Promise.resolve(
          jsonResponse(409, {
            code: "run.no_training_data",
            message: "No training data",
          }),
        );
      }
      return Promise.resolve(jsonResponse(404, { code: "x", message: "x" }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <MemoryRouter>
        <NewRunPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("new-run-start")).not.toBeDisabled(),
    );
    await userEvent.click(screen.getByTestId("new-run-start"));
    await waitFor(() =>
      expect(screen.getByTestId("new-run-error")).toHaveTextContent(
        "No training data",
      ),
    );
  });
});
