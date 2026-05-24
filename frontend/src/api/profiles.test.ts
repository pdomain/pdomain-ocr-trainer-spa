// API client tests for the /api/profiles surface.

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  ApiError,
  createProfile,
  deleteProfile,
  fetchProfiles,
  migrateLegacy,
  updateProfile,
} from "./profiles";

function mockFetch(impl: (url: string, init?: RequestInit) => Response): void {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init?: RequestInit) =>
      Promise.resolve(impl(url, init)),
    ),
  );
}

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: () => Promise.resolve(body),
  } as Response;
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchProfiles", () => {
  it("returns the profile list envelope", async () => {
    mockFetch(() =>
      jsonResponse(200, {
        profiles: [{ name: "all", is_base: true }],
        has_legacy_layout: false,
      }),
    );
    const result = await fetchProfiles();
    expect(result.profiles[0].name).toBe("all");
    expect(result.has_legacy_layout).toBe(false);
  });
});

describe("createProfile", () => {
  it("POSTs the payload and returns the new profile", async () => {
    const spy = vi.fn((_url: string, _init?: RequestInit) =>
      jsonResponse(201, { name: "clogaelach", language: "ga" }),
    );
    mockFetch(spy);
    const result = await createProfile({ name: "Clogaelach", language: "ga" });
    expect(result.name).toBe("clogaelach");
    expect(spy).toHaveBeenCalledWith(
      "/api/profiles",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws ApiError carrying the error code on a 409", async () => {
    mockFetch(() =>
      jsonResponse(409, { code: "profile.exists", message: "exists" }),
    );
    await expect(createProfile({ name: "dup" })).rejects.toMatchObject({
      code: "profile.exists",
      status: 409,
    });
  });
});

describe("updateProfile", () => {
  it("PATCHes the named profile", async () => {
    const spy = vi.fn((_url: string, _init?: RequestInit) =>
      jsonResponse(200, { name: "clogaelach", typeface: null }),
    );
    mockFetch(spy);
    await updateProfile("clogaelach", { typeface: null });
    expect(spy).toHaveBeenCalledWith(
      "/api/profiles/clogaelach",
      expect.objectContaining({ method: "PATCH" }),
    );
  });
});

describe("deleteProfile", () => {
  it("DELETEs and resolves on 204", async () => {
    mockFetch(() => ({ ok: true, status: 204 }) as Response);
    await expect(deleteProfile("clogaelach")).resolves.toBeUndefined();
  });

  it("throws ApiError on a 409 guard", async () => {
    mockFetch(() =>
      jsonResponse(409, { code: "profile.is_base", message: "no" }),
    );
    await expect(deleteProfile("all")).rejects.toBeInstanceOf(ApiError);
  });
});

describe("migrateLegacy", () => {
  it("POSTs to the migrate-legacy endpoint", async () => {
    const spy = vi.fn(() => ({ ok: true, status: 204 }) as Response);
    mockFetch(spy);
    await migrateLegacy();
    expect(spy).toHaveBeenCalledWith(
      "/api/profiles/migrate-legacy",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
