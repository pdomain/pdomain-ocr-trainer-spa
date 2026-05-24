// publish.ts API client tests — error envelope handling.
// Spec: 09-hf-integration §5–§6, M11.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { publishDataset } from "./publish";
import { ApiError } from "./profiles";

function errorResponse(status: number, body: unknown): Response {
  return {
    ok: false,
    status,
    statusText: "",
    json: () => Promise.resolve(body),
  } as Response;
}

function okResponse(body: unknown): Response {
  return {
    ok: true,
    status: 200,
    statusText: "",
    json: () => Promise.resolve(body),
  } as Response;
}

describe("publish API client", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("throws ApiError with correctly-ordered code/message/status on error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          errorResponse(409, {
            code: "publish.license_missing",
            message: "License is required",
          }),
        ),
      ),
    );
    await expect(
      publishDataset({
        profile: "p",
        task: "recognition",
        repo: "owner/repo",
        visibility: "private",
        license: "Apache-2.0",
      }),
    ).rejects.toMatchObject({
      // status must be a number, not coerced into the message slot
      status: 409,
      code: "publish.license_missing",
      message: "License is required",
    });
  });

  it("wraps the thrown value as an ApiError instance", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(errorResponse(500, { message: "boom" }))),
    );
    const err = await publishDataset({
      profile: "p",
      task: "recognition",
      repo: "owner/repo",
      visibility: "private",
      license: "Apache-2.0",
    }).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
  });

  it("returns the parsed body on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(okResponse({ run_id: "r1", job_id: "j1" }))),
    );
    await expect(
      publishDataset({
        profile: "p",
        task: "recognition",
        repo: "owner/repo",
        visibility: "private",
        license: "Apache-2.0",
      }),
    ).resolves.toEqual({ run_id: "r1", job_id: "j1" });
  });
});
