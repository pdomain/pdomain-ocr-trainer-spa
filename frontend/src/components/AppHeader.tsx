// AppHeader — minimal app chrome: header bar + sidebar nav (spec 13 §4.1).
//
// Spec 03 §6.1 calls for the full pd-ui `AppShell` + `TopNav`; that
// integration is a later milestone. M9 ships the minimal header the
// driver-contract conformance test (spec 13 §5) needs: a stable
// `header-bar` with a version badge and help button, and a
// `sidebar-nav` with one link per spec 13 §4.1 section.
//
// The active-profile selector (`header-profile-selector`) and the jobs
// SSE badge (`header-jobs-badge`) are intentionally NOT here — they
// depend on larger features and are waived in the conformance test
// until their milestone lands.

import { NavLink } from "react-router-dom";
import { getAppEnv } from "../lib/appEnv";

/** Sidebar sections, spec 13 §4.1 — `sidebar-nav-{section}`. */
const NAV_SECTIONS: ReadonlyArray<{ section: string; label: string; to: string }> = [
  { section: "profiles", label: "Profiles", to: "/profiles" },
  { section: "datasets", label: "Datasets", to: "/profiles" },
  { section: "runs", label: "Runs", to: "/runs" },
  { section: "models", label: "Models", to: "/models" },
  { section: "eval", label: "Eval", to: "/eval" },
  { section: "publish", label: "Publish", to: "/publish" },
  { section: "settings", label: "Settings", to: "/settings" },
];

export interface AppHeaderProps {
  /** Opens the hotkey help dialog (owned by AppChrome). */
  onOpenHelp: () => void;
}

/** Minimal header bar + sidebar nav for the driver contract (spec 13 §4.1). */
export function AppHeader({ onOpenHelp }: AppHeaderProps): JSX.Element {
  const env = getAppEnv();
  return (
    <>
      <header
        data-testid="header-bar"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0.5rem 1rem",
          borderBottom: "1px solid var(--border, #ddd)",
        }}
      >
        <strong>pd-ocr-trainer</strong>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <span data-testid="header-app-version" title="App version">
            v{env.version}
          </span>
          <button
            type="button"
            data-testid="header-help-button"
            aria-label="Keyboard shortcuts"
            onClick={onOpenHelp}
          >
            ?
          </button>
        </div>
      </header>
      <nav data-testid="sidebar-nav" aria-label="Primary">
        <ul style={{ display: "flex", gap: "0.75rem", listStyle: "none", padding: "0.5rem 1rem", margin: 0 }}>
          {NAV_SECTIONS.map(({ section, label, to }) => (
            <li key={section}>
              <NavLink data-testid={`sidebar-nav-${section}`} to={to}>
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </>
  );
}
