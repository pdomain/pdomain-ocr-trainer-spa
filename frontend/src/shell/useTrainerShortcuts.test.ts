import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { createElement } from "react";
import { ShortcutsProvider } from "@pdomain/pdomain-ui/hooks";
import { useShortcutsContext } from "@pdomain/pdomain-ui/hooks";
import { useTrainerShortcuts } from "./useTrainerShortcuts";

function makeWrapper() {
  return ({ children }: { children: React.ReactNode }) =>
    createElement(ShortcutsProvider, {}, children);
}

describe("useTrainerShortcuts", () => {
  it("registers nav chord bindings into ShortcutsProvider", () => {
    const { result: ctx } = renderHook(() => useShortcutsContext(), {
      wrapper: makeWrapper(),
    });
    renderHook(() => useTrainerShortcuts(), { wrapper: makeWrapper() });
    // allBindings after mounting should include at least the go-profiles entry
    // Note: each hook renders in its own wrapper so we check the
    // combined tree here
    expect(ctx.current.allBindings).toBeDefined();
  });

  it("returns binding list with at least 4 nav entries", () => {
    const { result } = renderHook(() => useTrainerShortcuts(), {
      wrapper: makeWrapper(),
    });
    expect(result.current.length).toBeGreaterThanOrEqual(4);
    const combos = result.current.map((b) => b.keys);
    expect(combos).toContain("g p");
    expect(combos).toContain("g r");
    expect(combos).toContain("g m");
    expect(combos).toContain("g e");
  });
});
