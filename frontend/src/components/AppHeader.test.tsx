// AppHeader — minimal app-chrome tests (spec 13 §4.1 driver contract).

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppHeader } from "./AppHeader";

function renderHeader(onOpenHelp = vi.fn()) {
  return render(
    <MemoryRouter>
      <AppHeader onOpenHelp={onOpenHelp} />
    </MemoryRouter>,
  );
}

afterEach(() => {
  delete window.__APP_ENV__;
});

describe("AppHeader", () => {
  it("renders the header bar with version badge and help button", () => {
    renderHeader();
    expect(screen.getByTestId("header-bar")).toBeInTheDocument();
    expect(screen.getByTestId("header-app-version")).toBeInTheDocument();
    expect(screen.getByTestId("header-help-button")).toBeInTheDocument();
  });

  it("shows the app version from window.__APP_ENV__ when present", () => {
    window.__APP_ENV__ = { version: "9.9.9" };
    renderHeader();
    expect(screen.getByTestId("header-app-version")).toHaveTextContent("v9.9.9");
  });

  it("falls back to a dev version when __APP_ENV__ is absent", () => {
    renderHeader();
    expect(screen.getByTestId("header-app-version")).toHaveTextContent("vdev");
  });

  it("calls onOpenHelp when the help button is clicked", () => {
    const onOpenHelp = vi.fn();
    renderHeader(onOpenHelp);
    screen.getByTestId("header-help-button").click();
    expect(onOpenHelp).toHaveBeenCalledOnce();
  });

  it("renders a sidebar-nav link for every driver-contract section", () => {
    renderHeader();
    expect(screen.getByTestId("sidebar-nav")).toBeInTheDocument();
    for (const section of [
      "profiles",
      "datasets",
      "runs",
      "models",
      "eval",
      "publish",
      "settings",
    ]) {
      expect(screen.getByTestId(`sidebar-nav-${section}`)).toBeInTheDocument();
    }
  });
});
