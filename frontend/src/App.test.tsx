// App smoke test — renders the profiles route without crashing.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ profiles: [], has_legacy_layout: false }),
      } as Response),
    ),
  );
});

describe("App", () => {
  it("renders the profiles page at the default route", async () => {
    render(<App />);
    expect(screen.getByTestId("app-root")).toBeInTheDocument();
    expect(await screen.findByTestId("profiles-page")).toBeInTheDocument();
  });
});
