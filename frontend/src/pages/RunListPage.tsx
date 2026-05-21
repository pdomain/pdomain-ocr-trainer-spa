// RunListPage — the run inventory table (spec 06 §8, route /runs).

import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge, Button, Card } from "@concavetrillion/pd-ui/primitives";
import type { BadgeVariant } from "@concavetrillion/pd-ui/primitives";
import { fetchRuns } from "../api/runs";
import type { Run, RunStatus } from "../api/runs";

// pd-ui Badge exposes only default | primary | danger — map run statuses
// onto that palette. The status text itself stays the precise signal
// (spec 12 §6 — never colour alone).
const STATUS_VARIANT: Record<RunStatus, BadgeVariant> = {
  pending: "default",
  running: "primary",
  succeeded: "primary",
  failed: "danger",
  cancelled: "default",
};

function formatDuration(start: string, end: string | null): string {
  const startMs = Date.parse(start);
  const endMs = end ? Date.parse(end) : Date.now();
  if (Number.isNaN(startMs) || Number.isNaN(endMs)) return "—";
  const secs = Math.max(0, Math.round((endMs - startMs) / 1000));
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

export function RunListPage(): JSX.Element {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [profileFilter, setProfileFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetchRuns();
      setRuns(resp.runs);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load runs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(
    () =>
      runs.filter(
        (r) =>
          (profileFilter === "" || r.profile.includes(profileFilter)) &&
          (statusFilter === "" || r.status === statusFilter),
      ),
    [runs, profileFilter, statusFilter],
  );

  return (
    <div data-testid="run-list-page">
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <h1>Runs</h1>
        <Button data-testid="run-list-refresh" variant="ghost" onClick={() => void load()}>
          Refresh
        </Button>
      </header>

      <div style={{ display: "flex", gap: "0.5rem", margin: "0.5rem 0" }}>
        <input
          data-testid="run-list-filter-profile"
          placeholder="Filter profile…"
          value={profileFilter}
          onChange={(e) => setProfileFilter(e.target.value)}
        />
        <select
          data-testid="run-list-filter-status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All statuses</option>
          <option value="pending">pending</option>
          <option value="running">running</option>
          <option value="succeeded">succeeded</option>
          <option value="failed">failed</option>
          <option value="cancelled">cancelled</option>
        </select>
      </div>

      {error && (
        <p data-testid="run-list-error" role="alert">
          {error}
        </p>
      )}
      {loading && <p data-testid="run-list-loading">Loading…</p>}

      <Card>
        <table data-testid="run-list-table">
          <thead>
            <tr>
              <th>Started</th>
              <th>Profile</th>
              <th>Task</th>
              <th>Kind</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Model</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={r.id} data-testid={`run-list-row-${r.id}`}>
                <td>{new Date(r.started_at).toLocaleString()}</td>
                <td>{r.profile}</td>
                <td>{r.task}</td>
                <td>{r.kind}</td>
                <td>
                  <Badge data-testid={`run-list-row-${r.id}-status`} variant={STATUS_VARIANT[r.status]}>
                    {r.status}
                  </Badge>
                </td>
                <td>{formatDuration(r.started_at, r.finished_at)}</td>
                <td>
                  <a href={`/runs/${r.id}`} data-testid={`run-list-row-${r.id}-link`}>
                    {r.model_name}
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && !loading && (
          <p data-testid="run-list-empty">No runs yet.</p>
        )}
      </Card>
    </div>
  );
}
