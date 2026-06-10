import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { createElement } from "react";
import {
  ShortcutsProvider,
  useShortcutsContext,
} from "@pdomain/pdomain-ui/hooks";
import { useTrainerShortcuts } from "./useTrainerShortcuts";

function makeWrapper() {
  return ({ children }: { children: React.ReactNode }) =>
    createElement(ShortcutsProvider, {}, children);
}

describe("useTrainerShortcuts", () => {
  it("trainer bindings are visible in the shared ShortcutsProvider context", () => {
    // Both hooks share ONE wrapper so useTrainerShortcuts' registrations are
    // visible to useShortcutsContext in the same tree.  The previous version
    // mounted them in SEPARATE renderHook wrappers — different provider trees —
    // so ctx.current.allBindings never contained the trainer bindings.
    const wrapper = makeWrapper();
    let trainerBindings: ReturnType<typeof useTrainerShortcuts> = [];
    let ctxBindings: ReturnType<typeof useShortcutsContext>["allBindings"] = [];

    renderHook(
      () => {
        trainerBindings = useTrainerShortcuts();
        const ctx = useShortcutsContext();
        ctxBindings = ctx.allBindings;
      },
      { wrapper },
    );

    // After mounting, the context must contain the trainer bindings.
    const registeredCombos = ctxBindings.map((b) => b.keys);
    expect(registeredCombos).toContain("g p");
    expect(registeredCombos).toContain("g r");
    expect(registeredCombos).toContain("g m");
    expect(registeredCombos).toContain("g e");
    // The hook's own return value must also be non-empty.
    expect(trainerBindings.length).toBeGreaterThanOrEqual(4);
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
