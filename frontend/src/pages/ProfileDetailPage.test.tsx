// ProfileDetailPage tests — the Defaults tab + run-args editor (spec 04 §3, §5).

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ProfileDetailPage } from "./ProfileDetailPage";

function jsonResponse(status: number, body: unknown, headers: HeadersInit = {}): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    headers: new Headers(headers),
    json: () => Promise.resolve(body),
  } as Response;
}

const DETECTION_SEED = {
  arch: "db_resnet50",
  epochs: 100,
  batch_size: 2,
  rotation: false,
};
const RECOGNITION_SEED = {
  arch: "crnn_vgg16_bn",
  epochs: 10,
  vocab_library: ["french"],
  custom_characters: "",
};

// An in-memory training_defaults.json keyed by task, so PUT then GET round-trips.
function makeFetch(saved: Record<string, Record<string, unknown>> = {}) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    const task = url.includes("/detection") ? "detection" : "recognition";
    const seed = task === "detection" ? DETECTION_SEED : RECOGNITION_SEED;

    if (url.endsWith("/seed")) {
      return Promise.resolve(jsonResponse(200, { task, args: { ...seed } }));
    }
    if (method === "PUT") {
      saved[task] = JSON.parse(String(init?.body)) as Record<string, unknown>;
      return Promise.resolve(jsonResponse(200, { task, args: saved[task] }));
    }
    if (method === "DELETE") {
      delete saved[task];
      return Promise.resolve(jsonResponse(204, null));
    }
    // GET saved defaults
    if (saved[task]) {
      return Promise.resolve(jsonResponse(200, { task, args: saved[task] }));
    }
    return Promise.resolve(
      jsonResponse(404, { code: "training_defaults.not_set", message: "" }),
    );
  });
}

function renderPage(name = "clogaelach") {
  return render(
    <MemoryRouter initialEntries={[`/profiles/${name}`]}>
      <Routes>
        <Route path="/profiles/:name" element={<ProfileDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe("ProfileDetailPage", () => {
  it("renders the tab strip including a Defaults tab", () => {
    vi.stubGlobal("fetch", makeFetch());
    renderPage();
    expect(screen.getByTestId("profile-detail-page")).toBeTruthy();
    expect(screen.getByTestId("profile-detail-tab-defaults")).toBeTruthy();
  });

  it("Defaults tab prefills the detection seed when nothing is saved", async () => {
    vi.stubGlobal("fetch", makeFetch());
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByTestId("profile-detail-tab-defaults"));
    await waitFor(() => {
      const epochs = screen.getByTestId(
        "profile-detail-defaults-field-epochs",
      ) as HTMLInputElement;
      expect(epochs.value).toBe("100");
    });
    expect(screen.getByTestId("profile-detail-defaults-source").textContent).toContain(
      "seed",
    );
  });

  it("round-trips: edit + save detection defaults, reopen prefills the saved value", async () => {
    const saved: Record<string, Record<string, unknown>> = {};
    vi.stubGlobal("fetch", makeFetch(saved));
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByTestId("profile-detail-tab-defaults"));
    const epochs = await screen.findByTestId("profile-detail-defaults-field-epochs");
    await user.clear(epochs);
    await user.type(epochs, "42");
    await user.click(screen.getByTestId("profile-detail-defaults-save"));
    await waitFor(() => {
      expect(screen.getByTestId("profile-detail-defaults-status")).toBeTruthy();
    });
    expect(saved.detection?.epochs).toBe(42);

    // Switch away and back — the saved value is prefilled.
    await user.click(screen.getByTestId("profile-detail-defaults-task-recognition"));
    await user.click(screen.getByTestId("profile-detail-defaults-task-detection"));
    await waitFor(() => {
      const reopened = screen.getByTestId(
        "profile-detail-defaults-field-epochs",
      ) as HTMLInputElement;
      expect(reopened.value).toBe("42");
    });
    expect(screen.getByTestId("profile-detail-defaults-source").textContent).toContain(
      "saved",
    );
  });

  it("recognition defaults round-trip independently of detection", async () => {
    const saved: Record<string, Record<string, unknown>> = {};
    vi.stubGlobal("fetch", makeFetch(saved));
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByTestId("profile-detail-tab-defaults"));
    await user.click(screen.getByTestId("profile-detail-defaults-task-recognition"));
    const epochs = await screen.findByTestId("profile-detail-defaults-field-epochs");
    await user.clear(epochs);
    await user.type(epochs, "25");
    await user.click(screen.getByTestId("profile-detail-defaults-save"));
    await waitFor(() => expect(saved.recognition?.epochs).toBe(25));
    expect(saved.detection).toBeUndefined();
  });

  it("Reset to seed deletes saved defaults and falls back to the seed", async () => {
    const saved: Record<string, Record<string, unknown>> = {
      detection: { ...DETECTION_SEED, epochs: 7 },
    };
    vi.stubGlobal("fetch", makeFetch(saved));
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByTestId("profile-detail-tab-defaults"));
    await waitFor(() => {
      const epochs = screen.getByTestId(
        "profile-detail-defaults-field-epochs",
      ) as HTMLInputElement;
      expect(epochs.value).toBe("7");
    });
    await user.click(screen.getByTestId("profile-detail-defaults-reset"));
    await waitFor(() => {
      const epochs = screen.getByTestId(
        "profile-detail-defaults-field-epochs",
      ) as HTMLInputElement;
      expect(epochs.value).toBe("100");
    });
    expect(saved.detection).toBeUndefined();
  });
});
