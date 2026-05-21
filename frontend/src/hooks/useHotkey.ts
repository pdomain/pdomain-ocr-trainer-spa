// useHotkey — the mandatory wrapper over react-hotkeys-hook (spec 12 §1).
//
// All bindings MUST go through this wrapper, never raw `useHotkeys`:
//
//   - it records the binding into the global hotkey registry so the `?`
//     help dialog can enumerate it,
//   - it rejects duplicate (scope, combo) pairs at mount (spec 12 §4),
//   - `enableOnFormTags` defaults to false; opt in per binding when a
//     hotkey must fire inside an input (e.g. Ctrl+S in the run form).

import { useEffect } from "react";
import { useHotkeys } from "react-hotkeys-hook";
import type { HotkeyCallback } from "react-hotkeys-hook";
import { registerHotkey } from "../lib/hotkeyRegistry";

export interface UseHotkeyOptions {
  /** Scope this binding belongs to — see `hotkeyRegistry.SCOPE_ORDER`. */
  scope: string;
  /** Key combination, react-hotkeys-hook syntax (e.g. "g p", "ctrl+s"). */
  combo: string;
  /** Human description shown in the `?` help dialog. */
  description: string;
  /** Allow the binding to fire while a form element is focused. */
  enableOnFormTags?: boolean;
  /** Disable the binding without unregistering it from the help dialog. */
  enabled?: boolean;
  /** Prevent the browser default for the combo. */
  preventDefault?: boolean;
  /**
   * Register the entry for the help dialog only — do NOT bind a live
   * `useHotkeys` listener. Used for multi-key navigation chords (`g p`)
   * whose sequence handling lands in a later milestone (spec 12 §2).
   */
  displayOnly?: boolean;
}

/**
 * Register a scoped hotkey.
 *
 * The binding is added to the global registry on mount (so the help
 * dialog sees it) and removed on unmount. The handler only fires while
 * `enabled` is not explicitly false.
 */
export function useHotkey(
  options: UseHotkeyOptions,
  handler: HotkeyCallback,
): void {
  const {
    scope,
    combo,
    description,
    enableOnFormTags = false,
    enabled = true,
    preventDefault = false,
    displayOnly = false,
  } = options;

  useEffect(() => {
    return registerHotkey({ scope, combo, description });
  }, [scope, combo, description]);

  // `useHotkeys` is always called (rules of hooks); `displayOnly`
  // bindings simply pass `enabled: false` so no listener attaches.
  useHotkeys(combo, handler, {
    enabled: enabled && !displayOnly,
    enableOnFormTags,
    preventDefault,
  });
}
