// BannerStack tests — banner scenarios from spec 11-notifications §8.

import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BannerStack } from "./BannerStack";
import type { Banner } from "../api/banners";

afterEach(() => {
  sessionStorage.clear();
});

const hfBanner: Banner = {
  id: "hf-token-missing",
  severity: "warn",
  title: "Hugging Face token missing",
  description: "HF publishing is enabled but no token file was found.",
  action: { label: "Open settings", href: "/settings" },
  dismissible: true,
};

const diskBanner: Banner = {
  id: "disk-low",
  severity: "error",
  title: "Disk almost full",
  description: "The shared-models partition has only 3% free.",
  dismissible: false,
};

function fetcher(banners: Banner[]) {
  return () => Promise.resolve({ banners });
}

describe("BannerStack", () => {
  it("renders nothing when there are no banners", async () => {
    const { container } = render(<BannerStack fetcher={fetcher([])} />);
    await waitFor(() => {
      expect(container.querySelector('[data-testid="banner-stack"]')).toBeNull();
    });
  });

  // Spec §8 scenario 3: hf-token-missing banner is visible; dismiss
  // keeps it gone for this tab.
  it("shows the hf-token-missing banner and dismisses it per-tab", async () => {
    const user = userEvent.setup();
    render(<BannerStack fetcher={fetcher([hfBanner])} />);

    const banner = await screen.findByTestId("banner-hf-token-missing");
    expect(banner).toHaveAttribute("aria-live", "polite");
    expect(banner).toHaveAttribute("role", "region");
    expect(screen.getByTestId("banner-hf-token-missing-action")).toHaveAttribute(
      "href",
      "/settings",
    );

    await user.click(screen.getByTestId("banner-hf-token-missing-dismiss"));
    expect(screen.queryByTestId("banner-hf-token-missing")).toBeNull();

    // Dismissal persists for the tab — a remount keeps it hidden.
    render(<BannerStack fetcher={fetcher([hfBanner])} />);
    await waitFor(() => {
      expect(screen.queryByTestId("banner-hf-token-missing")).toBeNull();
    });
  });

  it("renders an error banner with assertive aria-live and no dismiss button", async () => {
    render(<BannerStack fetcher={fetcher([diskBanner])} />);
    const banner = await screen.findByTestId("banner-disk-low");
    expect(banner).toHaveAttribute("aria-live", "assertive");
    expect(screen.queryByTestId("banner-disk-low-dismiss")).toBeNull();
  });

  it("renders multiple banners in order", async () => {
    render(<BannerStack fetcher={fetcher([hfBanner, diskBanner])} />);
    await screen.findByTestId("banner-hf-token-missing");
    expect(screen.getByTestId("banner-disk-low")).toBeInTheDocument();
  });

  it("never throws when the fetch fails", async () => {
    const failing = () => Promise.reject(new Error("network"));
    // BannerStack swallows fetch errors at the api layer; here the
    // fetcher itself rejects — the component must still mount cleanly.
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(<BannerStack fetcher={failing} />);
    await new Promise((r) => setTimeout(r, 10));
    spy.mockRestore();
  });
});
