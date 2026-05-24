// Profiles store tests — uses the factory for isolated state per test.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { createProfilesStore } from "./profilesStore";

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: () => Promise.resolve(body),
  } as Response;
}

const ALL_ONLY = {
  profiles: [{ name: "all", is_base: true }],
  has_legacy_layout: false,
};

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe("profilesStore", () => {
  it("load() populates profiles and clears loading", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(200, ALL_ONLY))),
    );
    const store = createProfilesStore();
    await store.getState().load();
    const state = store.getState();
    expect(state.profiles).toHaveLength(1);
    expect(state.profiles[0].name).toBe("all");
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it("load() records the error message on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new Error("network down"))),
    );
    const store = createProfilesStore();
    await store.getState().load();
    expect(store.getState().error).toBe("network down");
    expect(store.getState().loading).toBe(false);
  });

  it("create() refreshes the list after a successful POST", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(201, { name: "clogaelach" }))
      .mockResolvedValueOnce(
        jsonResponse(200, {
          profiles: [{ name: "all" }, { name: "clogaelach" }],
          has_legacy_layout: false,
        }),
      );
    vi.stubGlobal("fetch", fetchMock);
    const store = createProfilesStore();
    await store.getState().create({ name: "Clogaelach" });
    expect(store.getState().profiles.map((p) => p.name)).toContain(
      "clogaelach",
    );
  });

  it("create() surfaces and rethrows an API error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          jsonResponse(409, { code: "profile.exists", message: "x" }),
        ),
      ),
    );
    const store = createProfilesStore();
    await expect(store.getState().create({ name: "dup" })).rejects.toThrow();
    expect(store.getState().error).toBe("x");
  });

  it("remove() deletes then refreshes", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 204 } as Response)
      .mockResolvedValueOnce(jsonResponse(200, ALL_ONLY));
    vi.stubGlobal("fetch", fetchMock);
    const store = createProfilesStore();
    await store.getState().remove("clogaelach");
    expect(store.getState().profiles).toHaveLength(1);
  });
});
