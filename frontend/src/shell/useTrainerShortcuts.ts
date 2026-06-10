import { useShortcuts } from "@pdomain/pdomain-ui/hooks";
import type { ShortcutBinding } from "@pdomain/pdomain-ui/hooks";

// No-op handler — these bindings are registered into ShortcutsProvider
// for display in the keybinds dock surface only. Real navigation handlers
// are wired via useNavigate in App.tsx (router-driven navigation).
const noop = () => {};

/**
 * Trainer nav chord bindings registered into ShortcutsProvider so they
 * appear in the AppShell keybinds dock surface.
 */
export const TRAINER_SHORTCUTS: ShortcutBinding[] = [
  { keys: "g p", label: "Go to Profiles", group: "nav", handler: noop },
  { keys: "g r", label: "Go to Runs", group: "nav", handler: noop },
  { keys: "g m", label: "Go to Models", group: "nav", handler: noop },
  { keys: "g e", label: "Go to Eval", group: "nav", handler: noop },
  { keys: "?", label: "Open shortcuts help", group: "global", handler: noop },
];

/** Register trainer shortcuts into the nearest ShortcutsProvider. */
export function useTrainerShortcuts(): ShortcutBinding[] {
  useShortcuts(TRAINER_SHORTCUTS);
  return TRAINER_SHORTCUTS;
}
