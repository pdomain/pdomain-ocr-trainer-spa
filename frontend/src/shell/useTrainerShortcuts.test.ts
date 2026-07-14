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
  it("registers only the '?' binding in the shared ShortcutsProvider context", () => {
    // Both hooks share ONE wrapper so useTrainerShortcuts' registrations are
    // visible to useShortcutsContext in the same tree.  The previous version
    // mounted them in SEPARATE renderHook wrappers — different provider trees —
    // so ctx.current.allBindings never contained the trainer bindings.
    //
    // The installed @pdomain/pdomain-ui useShortcuts only splits binding keys
    // on "+" and matches a single KeyboardEvent.key, so 2-key chords like
    // "g p" can never fire. Those chord bindings have been removed; only the
    // "?" binding (handled by ShortcutsProvider's own window listener) remains.
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

    // After mounting, the context must not contain the unfireable chords.
    const registeredCombos = ctxBindings.map((b) => b.keys);
    expect(registeredCombos).not.toContain("g p");
    expect(registeredCombos).not.toContain("g r");
    expect(registeredCombos).not.toContain("g m");
    expect(registeredCombos).not.toContain("g e");
    expect(registeredCombos).toContain("?");
    // The hook's own return value must also be exactly the "?" binding.
    expect(trainerBindings.length).toBe(1);
  });

  it("returns a binding list containing only '?'", () => {
    const { result } = renderHook(() => useTrainerShortcuts(), {
      wrapper: makeWrapper(),
    });
    const combos = result.current.map((b) => b.keys);
    expect(combos).toEqual(["?"]);
  });
});
