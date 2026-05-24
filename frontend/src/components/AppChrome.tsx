// AppChrome — shell-level notification + hotkey wiring (M8).
//
// Mounted once inside the Router. Owns:
//   - the global `?` hotkey + the HotkeyHelpDialog it opens,
//   - the `g {p,d,r,m,e,s}` navigation chords (scope `app`, spec 12 §2),
//   - the persistent banner stack (spec 11 §3).
// The sonner <Toaster> and useNotificationStream live in App.tsx itself
// (they do not need router context beyond navigation).

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useHotkey } from "../hooks/useHotkey";
import { AppHeader } from "./AppHeader";
import { BannerStack } from "./BannerStack";
import { HotkeyHelpDialog } from "./HotkeyHelpDialog";

/** Shell chrome: banners, global hotkeys, and the help dialog. */
export function AppChrome(): JSX.Element {
  const navigate = useNavigate();
  const [helpOpen, setHelpOpen] = useState(false);

  useHotkey(
    { scope: "app", combo: "shift+slash", description: "Show this dialog" },
    () => setHelpOpen((open) => !open),
  );
  // Navigation chords are spec'd (spec 12 §2) but two-key sequence
  // handling lands in a later milestone — registered display-only so
  // the help dialog lists them.
  useHotkey(
    {
      scope: "app",
      combo: "g p",
      description: "Go to Profiles",
      displayOnly: true,
    },
    () => navigate("/profiles"),
  );
  useHotkey(
    {
      scope: "app",
      combo: "g r",
      description: "Go to Runs",
      displayOnly: true,
    },
    () => navigate("/runs"),
  );
  useHotkey(
    {
      scope: "app",
      combo: "g m",
      description: "Go to Models",
      displayOnly: true,
    },
    () => navigate("/models"),
  );
  useHotkey(
    {
      scope: "app",
      combo: "g e",
      description: "Go to Eval",
      displayOnly: true,
    },
    () => navigate("/eval"),
  );

  return (
    <>
      <AppHeader onOpenHelp={() => setHelpOpen(true)} />
      <BannerStack />
      <HotkeyHelpDialog open={helpOpen} onClose={() => setHelpOpen(false)} />
    </>
  );
}
