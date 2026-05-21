// hotkeyRegistry tests — registration, dedup, scope grouping (spec 12 §1, §4).

import { afterEach, describe, expect, it } from "vitest";
import {
  DuplicateHotkeyError,
  _resetHotkeyRegistry,
  hotkeysByScope,
  listHotkeys,
  registerHotkey,
} from "./hotkeyRegistry";

afterEach(() => {
  _resetHotkeyRegistry();
});

describe("registerHotkey", () => {
  it("records a binding and removes it on unregister", () => {
    const off = registerHotkey({
      scope: "app",
      combo: "shift+slash",
      description: "Help",
    });
    expect(listHotkeys()).toHaveLength(1);
    off();
    expect(listHotkeys()).toHaveLength(0);
  });

  it("ref-counts identical re-registrations (StrictMode double mount)", () => {
    const off1 = registerHotkey({ scope: "app", combo: "j", description: "Down" });
    const off2 = registerHotkey({ scope: "app", combo: "j", description: "Down" });
    expect(listHotkeys()).toHaveLength(1);
    off1();
    expect(listHotkeys()).toHaveLength(1); // still one ref
    off2();
    expect(listHotkeys()).toHaveLength(0);
  });

  it("throws on a conflicting (scope, combo) with a different description", () => {
    registerHotkey({ scope: "kanban", combo: "x", description: "Toggle select" });
    expect(() =>
      registerHotkey({ scope: "kanban", combo: "x", description: "Something else" }),
    ).toThrow(DuplicateHotkeyError);
  });

  it("allows the same combo in two different scopes", () => {
    registerHotkey({ scope: "kanban", combo: "r", description: "Rescan" });
    registerHotkey({ scope: "models-list", combo: "r", description: "Rename" });
    expect(listHotkeys()).toHaveLength(2);
  });
});

describe("hotkeysByScope", () => {
  it("groups entries in SCOPE_ORDER and omits empty scopes", () => {
    registerHotkey({ scope: "kanban", combo: "j", description: "Down" });
    registerHotkey({ scope: "app", combo: "shift+slash", description: "Help" });

    const groups = hotkeysByScope();
    expect(groups.map((g) => g.meta.scope)).toEqual(["app", "kanban"]);
  });
});
