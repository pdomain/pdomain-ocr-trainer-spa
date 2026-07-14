import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { createElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { TrainerRail } from "./TrainerRail";

function wrap(el: React.ReactElement) {
  return createElement(MemoryRouter, {}, el);
}

describe("TrainerRail", () => {
  it("renders sidebar-nav testid", () => {
    render(wrap(createElement(TrainerRail)));
    expect(screen.getByTestId("sidebar-nav")).toBeTruthy();
  });

  const sections = [
    "profiles",
    "datasets",
    "runs",
    "models",
    "eval",
    "publish",
  ];
  for (const section of sections) {
    it(`renders sidebar-nav-${section} testid`, () => {
      render(wrap(createElement(TrainerRail)));
      expect(screen.getByTestId(`sidebar-nav-${section}`)).toBeTruthy();
    });
  }

  it("does not render a settings nav link (no /settings route exists)", () => {
    render(wrap(createElement(TrainerRail)));
    expect(screen.queryByTestId("sidebar-nav-settings")).toBeNull();
  });
});
