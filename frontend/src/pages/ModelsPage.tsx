// ModelsPage — the trained-model registry table (spec 08 §6, route /models).

import { useCallback, useEffect, useMemo, useState } from "react";
import { Badge, Button, Card } from "@concavetrillion/pd-ui/primitives";
import { fetchModels, deleteModel } from "../api/models";
import type { ModelListItem } from "../api/models";

export function ModelsPage(): JSX.Element {
  const [models, setModels] = useState<ModelListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [profileFilter, setProfileFilter] = useState("");
  const [taskFilter, setTaskFilter] = useState("");
  const [legacyFilter, setLegacyFilter] = useState("both");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetchModels({
        includeLegacy: legacyFilter !== "no",
      });
      setModels(resp.models);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load models");
    } finally {
      setLoading(false);
    }
  }, [legacyFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(
    () =>
      models.filter((m) => {
        if (profileFilter && !m.model.profile.includes(profileFilter)) {
          return false;
        }
        if (taskFilter && m.model.task !== taskFilter) return false;
        if (legacyFilter === "yes" && !m.is_legacy) return false;
        return true;
      }),
    [models, profileFilter, taskFilter, legacyFilter],
  );

  const handleDelete = async (name: string) => {
    if (!window.confirm(`Delete model ${name}?`)) return;
    try {
      await deleteModel(name);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  return (
    <div data-testid="models-page">
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <h1>Models</h1>
        <Button
          data-testid="models-refresh"
          variant="ghost"
          onClick={() => void load()}
        >
          Refresh
        </Button>
      </header>

      <div style={{ display: "flex", gap: "0.5rem", margin: "0.5rem 0" }}>
        <input
          data-testid="models-filter-profile"
          placeholder="Filter profile…"
          value={profileFilter}
          onChange={(e) => setProfileFilter(e.target.value)}
        />
        <select
          data-testid="models-filter-task"
          value={taskFilter}
          onChange={(e) => setTaskFilter(e.target.value)}
        >
          <option value="">All tasks</option>
          <option value="detection">detection</option>
          <option value="recognition">recognition</option>
        </select>
        <select
          data-testid="models-filter-legacy"
          value={legacyFilter}
          onChange={(e) => setLegacyFilter(e.target.value)}
        >
          <option value="both">Legacy: both</option>
          <option value="yes">Legacy only</option>
          <option value="no">New only</option>
        </select>
      </div>

      {error && (
        <p data-testid="models-error" role="alert">
          {error}
        </p>
      )}
      {loading && <p data-testid="models-loading">Loading…</p>}

      <Card>
        <table data-testid="models-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Profile</th>
              <th>Task</th>
              <th>Language</th>
              <th>Typeface</th>
              <th>Sidecar</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(({ model, has_sidecar }) => (
              <tr key={model.name} data-testid={`models-row-${model.name}`}>
                <td>
                  <a
                    href={`/models/${encodeURIComponent(model.name)}`}
                    data-testid={`models-row-${model.name}-link`}
                  >
                    {model.name}
                  </a>
                </td>
                <td>{model.profile}</td>
                <td>{model.task}</td>
                <td>{model.language ?? "—"}</td>
                <td>{model.typeface ?? "—"}</td>
                <td>
                  {has_sidecar ? (
                    <Badge variant="default">ok</Badge>
                  ) : (
                    <Badge
                      data-testid={`models-row-${model.name}-sidecar-missing`}
                      variant="danger"
                    >
                      missing
                    </Badge>
                  )}
                </td>
                <td>
                  <a
                    href={`/eval?model=${encodeURIComponent(model.name)}`}
                    data-testid={`models-row-${model.name}-eval`}
                  >
                    Eval
                  </a>{" "}
                  <a
                    href={`/models/${encodeURIComponent(model.name)}`}
                    data-testid={`models-row-${model.name}-rename`}
                  >
                    Rename
                  </a>{" "}
                  <button
                    data-testid={`models-row-${model.name}-delete`}
                    onClick={() => void handleDelete(model.name)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && !loading && (
          <p data-testid="models-empty">No models yet.</p>
        )}
      </Card>
    </div>
  );
}
