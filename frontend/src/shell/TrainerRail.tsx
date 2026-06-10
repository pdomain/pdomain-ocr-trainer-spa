import { NavLink } from "react-router-dom";

const NAV_SECTIONS = [
  { section: "profiles", label: "Profiles", to: "/profiles" },
  { section: "datasets", label: "Datasets", to: "/profiles" },
  { section: "runs", label: "Runs", to: "/runs" },
  { section: "models", label: "Models", to: "/models" },
  { section: "eval", label: "Eval", to: "/eval" },
  { section: "publish", label: "Publish", to: "/publish" },
  { section: "settings", label: "Settings", to: "/settings" },
] as const;

/** Vertical nav for AppShell rail slot. Preserves spec-13 §4.1 sidebar-nav testids. */
export function TrainerRail(): React.JSX.Element {
  return (
    <nav
      data-testid="sidebar-nav"
      aria-label="Primary"
      style={{
        display: "flex",
        flexDirection: "column",
        padding: "0.5rem 0",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {NAV_SECTIONS.map(({ section, label, to }) => (
        <NavLink
          key={section}
          data-testid={`sidebar-nav-${section}`}
          to={to}
          style={({ isActive }) => ({
            display: "block",
            padding: "0.4rem 0.75rem",
            fontSize: 12,
            fontWeight: isActive ? 600 : 400,
            color: isActive ? "var(--accent)" : "var(--ink-2)",
            textDecoration: "none",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          })}
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
