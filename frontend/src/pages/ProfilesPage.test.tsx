// ProfilesPage tests — exercises acceptance scenarios 1 & 3 at the UI layer
// and asserts the driver-contract testids (spec 13 §4.2).

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ProfilesPage } from "./ProfilesPage";
import { useProfilesStore } from "../stores/profilesStore";

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: () => Promise.resolve(body),
  } as Response;
}

const profile = (name: string, extra: Record<string, unknown> = {}) => ({
  name,
  display_name: name,
  language: null,
  typeface: null,
  is_base: name === "all",
  has_training_data: false,
  has_validation_data: false,
  counts: {
    detection_train_pages: 0,
    detection_val_pages: 0,
    recognition_train_crops: 0,
    recognition_val_crops: 0,
    typeface_train_crops: 0,
    typeface_val_crops: 0,
    glyph_train_crops: 0,
    glyph_val_crops: 0,
  },
  ...extra,
});

beforeEach(() => {
  vi.unstubAllGlobals();
  useProfilesStore.setState({
    profiles: [],
    hasLegacyLayout: false,
    loading: false,
    error: null,
  });
});

function renderPage() {
  return render(
    <MemoryRouter>
      <ProfilesPage />
    </MemoryRouter>,
  );
}

describe("ProfilesPage", () => {
  it("scenario 1: fresh install shows exactly one row, 'all'", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(200, {
            profiles: [profile("all")],
            has_legacy_layout: false,
          }),
        ),
      ),
    );
    renderPage();
    expect(await screen.findByTestId("profiles-row-all")).toBeInTheDocument();
    expect(screen.getAllByTestId(/^profiles-row-[^-]+$/)).toHaveLength(1);
  });

  it("exposes the driver-contract inventory testids", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(200, {
            profiles: [profile("all")],
            has_legacy_layout: false,
          }),
        ),
      ),
    );
    renderPage();
    await screen.findByTestId("profiles-row-all");
    expect(screen.getByTestId("profiles-page")).toBeInTheDocument();
    expect(screen.getByTestId("profiles-new-button")).toBeInTheDocument();
    expect(screen.getByTestId("profiles-table")).toBeInTheDocument();
    expect(screen.getByTestId("profiles-row-all-edit")).toBeInTheDocument();
    expect(screen.getByTestId("profiles-row-all-delete")).toBeInTheDocument();
  });

  it("the delete button is disabled for the base 'all' profile", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(200, {
            profiles: [profile("all")],
            has_legacy_layout: false,
          }),
        ),
      ),
    );
    renderPage();
    const del = await screen.findByTestId("profiles-row-all-delete");
    expect(del).toBeDisabled();
  });

  it("scenario 3: New profile button opens the create dialog", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(200, {
            profiles: [profile("all")],
            has_legacy_layout: false,
          }),
        ),
      ),
    );
    renderPage();
    await screen.findByTestId("profiles-row-all");
    await userEvent.click(screen.getByTestId("profiles-new-button"));
    expect(screen.getByTestId("profiles-edit-dialog")).toBeInTheDocument();
    expect(screen.getByTestId("profiles-edit-dialog-name")).toBeInTheDocument();
  });

  it("shows the Migrate Legacy button only when a legacy layout exists", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(200, {
            profiles: [profile("all")],
            has_legacy_layout: true,
          }),
        ),
      ),
    );
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId("profiles-migrate-legacy")).toBeInTheDocument(),
    );
  });
});
