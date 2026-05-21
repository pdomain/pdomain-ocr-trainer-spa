// Coverage smoke test for the error-message map (spec 11 §2.1).

import { describe, expect, it } from "vitest";
import { ERROR_CODES } from "../api/errors";
import type { ErrorEnvelope } from "../api/errors";
import { errorMessages, toastFromError, uncoveredErrorCodes } from "./errorMessages";

function envelope(code: string, overrides: Partial<ErrorEnvelope> = {}): ErrorEnvelope {
  return { code, message: `message for ${code}`, request_id: "req-1", ...overrides };
}

describe("errorMessages coverage", () => {
  it("has an entry for every backend error code", () => {
    // The spec mandates: drift between ERROR_CODES and errorMessages fails CI.
    expect(uncoveredErrorCodes()).toEqual([]);
  });

  it("every builder yields a kind=error toast with a non-empty description", () => {
    for (const code of ERROR_CODES) {
      const builder = errorMessages[code];
      expect(builder, `missing builder for ${code}`).toBeDefined();
      const toast = builder!(envelope(code));
      expect(toast.kind).toBe("error");
      // Spec §2: errors always carry an explicit description.
      expect(toast.description, `${code} has no description`).toBeTruthy();
      expect(toast.title.length).toBeGreaterThan(0);
      expect(toast.title.length).toBeLessThanOrEqual(50);
    }
  });
});

describe("toastFromError", () => {
  it("uses the per-code builder when one exists", () => {
    const toast = toastFromError(envelope("training.cuda_oom"));
    expect(toast.title).toBe("Out of GPU memory");
  });

  it("falls back to the envelope message + code for unknown codes", () => {
    const toast = toastFromError(envelope("totally.unknown", { message: "boom" }));
    expect(toast.kind).toBe("error");
    expect(toast.title).toBe("boom");
    expect(toast.description).toBe("totally.unknown");
  });

  it("interpolates detail counts for publish.license_missing", () => {
    const toast = toastFromError(
      envelope("publish.license_missing", {
        details: [
          { loc: ["row", "1"], msg: "no license" },
          { loc: ["row", "2"], msg: "no license" },
        ],
      }),
    );
    expect(toast.description).toContain("2 row");
  });
});
