// PublishDialog tests — canonical-case SPDX license IDs.
// Spec: 09-hf-integration §5. SPDX validation is case-sensitive (#18):
// the dialog must send canonical-case identifiers (e.g. "Apache-2.0").

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { PublishDialog } from "./PublishDialog";

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: () => Promise.resolve(body),
  } as Response;
}

// Canonical SPDX identifiers as defined by pd_book_tools.licenses.
// Plain "GPL-3.0" is a deprecated SPDX id and must NOT appear.
const CANONICAL_IDS = [
  "Apache-2.0",
  "MIT",
  "CC-BY-4.0",
  "CC-BY-SA-4.0",
  "CC-BY-NC-4.0",
  "CC0-1.0",
  "GPL-3.0-only",
  "GPL-3.0-or-later",
];

describe("PublishDialog SPDX license casing", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("every license <option> uses a canonical-case SPDX identifier", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise(() => {})),
    );
    render(
      <PublishDialog
        mode="dataset"
        profile="test-profile"
        task="recognition"
        onClose={() => {}}
        onSuccess={() => {}}
      />,
    );
    const select = screen.getByTestId(
      "publish-license-select",
    ) as HTMLSelectElement;
    const values = Array.from(select.options)
      .map((o) => o.value)
      .filter((v) => v !== "__custom__");
    // No all-lowercase ids leak through (e.g. "apache-2.0"): a canonical
    // SPDX id always carries at least one uppercase letter.
    for (const v of values) {
      expect(v).toMatch(/[A-Z]/);
    }
    // Deprecated plain GPL-3.0 must not be offered.
    expect(values).not.toContain("GPL-3.0");
    // All offered ids are in the canonical set.
    for (const v of values) {
      expect(CANONICAL_IDS).toContain(v);
    }
  });

  it("sends the canonical-case license id in the publish payload", async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(jsonResponse(202, { run_id: "r1", job_id: "j1" })),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(
      <PublishDialog
        mode="dataset"
        profile="test-profile"
        task="recognition"
        onClose={() => {}}
        onSuccess={() => {}}
      />,
    );

    fireEvent.change(screen.getByTestId("publish-repo-input"), {
      target: { value: "owner/ds" },
    });
    fireEvent.click(screen.getByTestId("publish-dialog-submit"));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const call = fetchMock.mock.calls[0];
    const body = JSON.parse((call[1] as RequestInit).body as string);
    // Default license must be canonical-case, not "apache-2.0".
    expect(body.license).toBe("Apache-2.0");
  });
});
