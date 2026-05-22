// PublishPage tests — datasets + models publish table and dialog.
// Spec: 09-hf-integration §5–§6, M11.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { PublishPage } from "./PublishPage";

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: () => Promise.resolve(body),
  } as Response;
}

const profile = (name = "test-profile") => ({
  name,
  language: "ga",
  typeface: "clogaelach",
  task_default: null,
  counts: {
    detection_train_pages: 0,
    detection_val_pages: 0,
    recognition_train_crops: 0,
    recognition_val_crops: 0,
  },
});

const modelItem = (name = "pd-ga-clogaelach-recognition-2026-01-01") => ({
  model: {
    name,
    profile: "test-profile",
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
});

function makeFetch(profiles: unknown[], models: unknown[]) {
  return vi.fn((url: string) => {
    if (typeof url === "string" && url.includes("/api/profiles")) {
      return Promise.resolve(jsonResponse(200, profiles));
    }
    if (typeof url === "string" && url.includes("/api/models")) {
      return Promise.resolve(jsonResponse(200, { models }));
    }
    return Promise.resolve(jsonResponse(200, {}));
  });
}

describe("PublishPage", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the publish page with datasets and models sections", async () => {
    vi.stubGlobal("fetch", makeFetch([profile()], [modelItem()]));
    render(
      <MemoryRouter>
        <PublishPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("publish-page")).toBeInTheDocument(),
    );
    // Datasets section heading
    expect(screen.getByText("Datasets")).toBeInTheDocument();
    // Models section heading
    expect(screen.getByText("Models")).toBeInTheDocument();
  });

  it("shows loading indicator while fetching", () => {
    // Never resolves
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    render(
      <MemoryRouter>
        <PublishPage />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("publish-page-loading")).toBeInTheDocument();
  });

  it("shows empty-profiles message when no profiles", async () => {
    vi.stubGlobal("fetch", makeFetch([], []));
    render(
      <MemoryRouter>
        <PublishPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("publish-no-profiles")).toBeInTheDocument(),
    );
  });

  it("shows empty-models message when no non-legacy models", async () => {
    vi.stubGlobal("fetch", makeFetch([profile()], []));
    render(
      <MemoryRouter>
        <PublishPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("publish-no-models")).toBeInTheDocument(),
    );
  });

  it("opens PublishDialog when a dataset Publish button is clicked", async () => {
    vi.stubGlobal("fetch", makeFetch([profile()], []));
    render(
      <MemoryRouter>
        <PublishPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("publish-page")).toBeInTheDocument(),
    );
    // Click the recognition dataset publish button
    fireEvent.click(
      screen.getByTestId("publish-dataset-test-profile-recognition"),
    );
    expect(screen.getByTestId("publish-dialog")).toBeInTheDocument();
    expect(
      screen.getByText(/Publish Dataset/i),
    ).toBeInTheDocument();
  });

  it("opens PublishDialog when a model Publish button is clicked", async () => {
    vi.stubGlobal("fetch", makeFetch([], [modelItem()]));
    render(
      <MemoryRouter>
        <PublishPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("publish-page")).toBeInTheDocument(),
    );
    fireEvent.click(
      screen.getByTestId(
        "publish-model-pd-ga-clogaelach-recognition-2026-01-01",
      ),
    );
    expect(screen.getByTestId("publish-dialog")).toBeInTheDocument();
    expect(screen.getByText(/Publish Model/i)).toBeInTheDocument();
  });

  it("closes the dialog when Cancel is clicked", async () => {
    vi.stubGlobal("fetch", makeFetch([profile()], []));
    render(
      <MemoryRouter>
        <PublishPage />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByTestId("publish-page")).toBeInTheDocument(),
    );
    fireEvent.click(
      screen.getByTestId("publish-dataset-test-profile-recognition"),
    );
    expect(screen.getByTestId("publish-dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("publish-dialog-cancel"));
    expect(screen.queryByTestId("publish-dialog")).not.toBeInTheDocument();
  });
});
