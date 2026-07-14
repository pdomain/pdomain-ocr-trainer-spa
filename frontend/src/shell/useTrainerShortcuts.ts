import { useShortcuts } from "@pdomain/pdomain-ui/hooks";
import type { ShortcutBinding } from "@pdomain/pdomain-ui/hooks";

// No-op handler — the installed @pdomain/pdomain-ui useShortcuts only
// splits a binding's `keys` string on "+" and matches a single
// KeyboardEvent.key, so it has no support for multi-key chords (e.g.
// "g p"). Nav chords are not registered here for that reason. The "?"
// binding below is a display-only placeholder: it's not dispatched by
// this hook's handler at all — ShortcutsProvider has its own window
// keydown listener that opens the cheatsheet on "?" directly.
// eslint-disable-next-line @typescript-eslint/no-empty-function -- intentional display-only no-op; see comment above
const noop = () => {};

/**
 * Trainer shortcut bindings registered into ShortcutsProvider so they
 * appear in the AppShell keybinds dock surface.
 */
export const TRAINER_SHORTCUTS: ShortcutBinding[] = [
  { keys: "?", label: "Open shortcuts help", group: "global", handler: noop },
];

/** Register trainer shortcuts into the nearest ShortcutsProvider. */
export function useTrainerShortcuts(): ShortcutBinding[] {
  useShortcuts(TRAINER_SHORTCUTS);
  return TRAINER_SHORTCUTS;
}
