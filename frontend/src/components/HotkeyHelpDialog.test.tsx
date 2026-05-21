// HotkeyHelpDialog tests — help-dialog scenarios from spec 12 §9.

import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HotkeyHelpDialog } from "./HotkeyHelpDialog";
import { _resetHotkeyRegistry, registerHotkey } from "../lib/hotkeyRegistry";

afterEach(() => {
  _resetHotkeyRegistry();
});

describe("HotkeyHelpDialog", () => {
  it("renders nothing while closed", () => {
    const { container } = render(
      <HotkeyHelpDialog open={false} onClose={vi.fn()} />,
    );
    expect(container.firstChild).toBeNull();
  });

  // Spec §9 scenario 1: pressing `?` opens the dialog with the current
  // scope's hotkeys; `Esc` closes it.
  it("lists registered hotkeys grouped by scope when open", () => {
    registerHotkey({
      scope: "app",
      combo: "shift+slash",
      description: "Show this dialog",
    });
    registerHotkey({ scope: "kanban", combo: "j", description: "Move focus down" });
    registerHotkey({
      scope: "kanban",
      combo: "t",
      description: "Move selected chips to Train",
    });

    render(<HotkeyHelpDialog open onClose={vi.fn()} />);

    const dialog = screen.getByTestId("hotkey-help-dialog");
    expect(dialog).toHaveAttribute("role", "dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");

    // Only scopes with bound hotkeys render a section (spec §8).
    expect(screen.getByTestId("hotkey-help-section-app")).toBeInTheDocument();
    expect(screen.getByTestId("hotkey-help-section-kanban")).toBeInTheDocument();
    expect(screen.queryByTestId("hotkey-help-section-run-detail")).toBeNull();

    expect(screen.getByText("Move selected chips to Train")).toBeInTheDocument();
  });

  it("closes when Escape is pressed", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    registerHotkey({ scope: "app", combo: "shift+slash", description: "Help" });

    render(<HotkeyHelpDialog open onClose={onClose} />);
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes via the close button", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    registerHotkey({ scope: "app", combo: "shift+slash", description: "Help" });

    render(<HotkeyHelpDialog open onClose={onClose} />);
    await user.click(screen.getByTestId("hotkey-help-close"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows an empty-state message when no hotkeys are registered", () => {
    render(<HotkeyHelpDialog open onClose={vi.fn()} />);
    expect(screen.getByTestId("hotkey-help-empty")).toBeInTheDocument();
  });
});
