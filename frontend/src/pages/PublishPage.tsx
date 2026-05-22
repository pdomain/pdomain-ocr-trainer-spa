// PublishPage — list publishable datasets + models and open PublishDialog.
// Spec: 09-hf-integration §5–§6, M11. Route: /publish.

import { useCallback, useEffect, useState } from "react";
import { Button, Card } from "@concavetrillion/pd-ui/primitives";
import { fetchModels } from "../api/models";
import type { ModelListItem } from "../api/models";
import { fetchProfiles } from "../api/profiles";
import type { Profile } from "../api/profiles";
import { PublishDialog } from "../components/PublishDialog";

type PublishTarget =
  | { kind: "dataset"; profile: Profile; task: string }
  | { kind: "model"; item: ModelListItem };

export function PublishPage(): JSX.Element {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [models, setModels] = useState<ModelListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [target, setTarget] = useState<PublishTarget | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [profilesResp, modelsResp] = await Promise.all([
        fetchProfiles(),
        fetchModels({ includeLegacy: false }),
      ]);
      setProfiles(profilesResp);
      setModels(modelsResp.models);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleSuccess = (runId: string, jobId: string) => {
    setTarget(null);
    setSuccessMsg(`Publish job started — run ${runId}, job ${jobId}`);
    setTimeout(() => setSuccessMsg(null), 6000);
  };

  if (loading) {
    return <div data-testid="publish-page-loading">Loading…</div>;
  }

  return (
    <div data-testid="publish-page">
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <h1>Publish to HuggingFace</h1>
        <Button
          data-testid="publish-refresh"
          variant="ghost"
          onClick={() => void load()}
        >
          Refresh
        </Button>
      </header>

      {error && (
        <div
          role="alert"
          data-testid="publish-page-error"
          style={{ color: "var(--color-error, red)", marginBottom: "1rem" }}
        >
          {error}
        </div>
      )}

      {successMsg && (
        <div
          role="status"
          data-testid="publish-success-msg"
          style={{ color: "green", marginBottom: "1rem" }}
        >
          {successMsg}
        </div>
      )}

      {/* Datasets section */}
      <section aria-labelledby="publish-datasets-heading">
        <h2 id="publish-datasets-heading">Datasets</h2>
        {profiles.length === 0 ? (
          <p data-testid="publish-no-profiles">No profiles found.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th>Profile</th>
                <th>Task</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {profiles.flatMap((profile) =>
                (
                  [
                    "recognition",
                    "detection",
                    "typeface-classification",
                    "glyph-classification",
                  ] as const
                ).map((task) => (
                  <tr key={`${profile.name}-${task}`}>
                    <td>{profile.name}</td>
                    <td>{task}</td>
                    <td>
                      <Button
                        variant="ghost"
                        data-testid={`publish-dataset-${profile.name}-${task}`}
                        onClick={() =>
                          setTarget({ kind: "dataset", profile, task })
                        }
                      >
                        Publish
                      </Button>
                    </td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        )}
      </section>

      {/* Models section */}
      <section aria-labelledby="publish-models-heading" style={{ marginTop: "2rem" }}>
        <h2 id="publish-models-heading">Models</h2>
        {models.length === 0 ? (
          <p data-testid="publish-no-models">No non-legacy models found.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th>Name</th>
                <th>Task</th>
                <th>Language</th>
                <th>Typeface</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {models.map((item) => (
                <tr key={item.model.name}>
                  <td>{item.model.name}</td>
                  <td>{item.model.task}</td>
                  <td>{item.model.language ?? "—"}</td>
                  <td>{item.model.typeface ?? "—"}</td>
                  <td>
                    <Button
                      variant="ghost"
                      data-testid={`publish-model-${item.model.name}`}
                      onClick={() => setTarget({ kind: "model", item })}
                    >
                      Publish
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Publish dialog */}
      {target !== null && (
        <PublishDialog
          mode={target.kind}
          profile={target.kind === "dataset" ? target.profile.name : undefined}
          task={target.kind === "dataset" ? target.task : undefined}
          modelName={
            target.kind === "model" ? target.item.model.name : undefined
          }
          defaultRepo={
            target.kind === "dataset"
              ? `/${target.profile.name}-${target.task}`
              : `/${target.item.model.name}`
          }
          onClose={() => setTarget(null)}
          onSuccess={handleSuccess}
        />
      )}
    </div>
  );
}
