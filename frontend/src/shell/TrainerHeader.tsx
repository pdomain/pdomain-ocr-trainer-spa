import {
  JobsPill,
  ShortcutsHelpButton,
  SettingsSlot,
  useUtilityDock,
} from "@pdomain/pdomain-ui/shell";
// ActiveJob is not deprecated. Its JSDoc in pdomain-ui shares a block with
// deprecated props, triggering a false positive. See lint-deviations.md.
import type { ActiveJob } from "@pdomain/pdomain-ui/shell";

export interface TrainerHeaderProps {
  // eslint-disable-next-line @typescript-eslint/no-deprecated
  activeJobs: ActiveJob[];
  appVersion: string;
}

/**
 * Custom header for the trainer SPA. Preserves all spec-13 §4.1 testids:
 * header-bar, header-app-version, header-help-button, header-jobs-badge.
 * Renders inside AppShell's header escape-hatch slot.
 */
export function TrainerHeader({
  activeJobs,
  appVersion,
}: TrainerHeaderProps): React.JSX.Element {
  const { toggle } = useUtilityDock();
  return (
    <header
      data-testid="header-bar"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: 52,
        padding: "0 1rem",
        background: "var(--bg-page)",
        borderBottom: "1px solid var(--border-1)",
        flexShrink: 0,
      }}
    >
      <strong style={{ color: "var(--ink-1)", fontSize: 13, fontWeight: 600 }}>
        OCR Trainer
      </strong>
      <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
        <span
          data-testid="header-app-version"
          title="App version"
          style={{ color: "var(--ink-3)", fontSize: 12 }}
        >
          v{appVersion}
        </span>
        {/* header-jobs-badge: wraps JobsPill to preserve spec-13 testid */}
        <span data-testid="header-jobs-badge">
          <JobsPill activeJobs={activeJobs} onClick={() => toggle("jobs")} />
        </span>
        {/* header-help-button: wraps ShortcutsHelpButton to preserve spec-13 testid */}
        <span data-testid="header-help-button">
          <ShortcutsHelpButton />
        </span>
        <SettingsSlot />
      </div>
    </header>
  );
}
