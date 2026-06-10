// App smoke test — renders the profiles route without crashing.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";

// Minimal mock for AppShell to avoid deep pdomain-ui render tree.
// The mock passes `main` through as children so the React Router routes
// still render — required for the profiles-page assertion.
vi.mock("@pdomain/pdomain-ui/shell", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@pdomain/pdomain-ui/shell")>();
  return {
    ...actual,
    AppShell: ({ main }: { main: React.ReactNode }) => (
      <div data-testid="app-shell">{main}</div>
    ),
    SuiteSiblingsProvider: ({ children }: { children: React.ReactNode }) => (
      <>{children}</>
    ),
    JobsPill: () => <button>jobs</button>,
    ShortcutsHelpButton: () => <button>?</button>,
    SettingsSlot: () => <button>⚙</button>,
    useUtilityDock: () => ({ toggle: vi.fn() }),
    createApiUIPrefsConfig: () => ({}),
  };
});

vi.mock("@pdomain/pdomain-ui/hooks", () => ({
  ShortcutsProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
  useShortcuts: vi.fn(),
}));

beforeEach(() => {
  // Stub fetch for all API calls the App makes on startup.
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (typeof url === "string" && url.includes("/api/jobs")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve([]),
        } as Response);
      }
      if (typeof url === "string" && url.includes("/api/banners")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ banners: [] }),
        } as Response);
      }
      // Default: profiles list + any other API
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ profiles: [], has_legacy_layout: false }),
      } as Response);
    }),
  );
});

function makeQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

describe("App", () => {
  it("renders app-shell root", async () => {
    const qc = makeQueryClient();
    render(
      <QueryClientProvider client={qc}>
        <App />
      </QueryClientProvider>,
    );
    expect(screen.getByTestId("app-shell")).toBeTruthy();
  });

  it("renders profiles-page at the root route", async () => {
    const qc = makeQueryClient();
    render(
      <QueryClientProvider client={qc}>
        <App />
      </QueryClientProvider>,
    );
    // AppShell mock passes `main` through, so the BrowserRouter renders
    // the default route ("/") which navigates to "/profiles" → ProfilesPage.
    expect(await screen.findByTestId("profiles-page")).toBeTruthy();
  });
});
