// ProfileDetailPage — per-profile detail with the Defaults tab (spec 04 §5, §3).
//
// M5 ships the "Defaults" tab: a task selector (detection / recognition) and
// the reusable RunArgsEditor pre-filled from the saved per-profile training
// defaults (or the pdomain-ocr-training seed when nothing is saved yet). Save → PUT;
// Reset → DELETE then re-load the seed. The Datasets / Runs / Models tabs are
// thin links into their own pages until later milestones flesh them out.

import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Button, Card } from "@pdomain/pdomain-ui/primitives";
import {
  deleteTrainingDefaults,
  fetchTrainingDefaultsOrSeed,
  putTrainingDefaults,
  type TrainingArgs,
} from "../api/profiles";
import { RunArgsEditor } from "../components/RunArgsEditor";

type Tab = "datasets" | "runs" | "models" | "defaults";
type DefaultsTask = "detection" | "recognition";

const TABS: { id: Tab; label: string }[] = [
  { id: "datasets", label: "Datasets" },
  { id: "runs", label: "Runs" },
  { id: "models", label: "Models" },
  { id: "defaults", label: "Defaults" },
];

export function ProfileDetailPage(): React.JSX.Element {
  const params = useParams<{ name: string }>();
  const profile = params.name ?? "all";

  const [tab, setTab] = useState<Tab>("datasets");
  const [task, setTask] = useState<DefaultsTask>("detection");
  const [args, setArgs] = useState<TrainingArgs | null>(null);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadDefaults = useCallback(
    async (forTask: DefaultsTask) => {
      setLoading(true);
      setError(null);
      try {
        const { args: loaded, saved: wasSaved } =
          await fetchTrainingDefaultsOrSeed(profile, forTask);
        setArgs(loaded);
        setSaved(wasSaved);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    },
    [profile],
  );

  useEffect(() => {
    if (tab === "defaults") void loadDefaults(task);
  }, [tab, task, loadDefaults]);

  const handleSave = async () => {
    if (!args) return;
    setBusy(true);
    setError(null);
    try {
      await putTrainingDefaults(profile, task, args);
      setSaved(true);
      setStatus(`Saved ${task} defaults for '${profile}'.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const handleReset = async () => {
    setBusy(true);
    setError(null);
    try {
      await deleteTrainingDefaults(profile, task);
      setStatus(`Reset ${task} defaults to the seed.`);
      await loadDefaults(task);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="profile-detail-page">
      <header>
        <h1>Profile — {profile}</h1>
      </header>

      <nav data-testid="profile-detail-tabs">
        {TABS.map((t) => (
          <Button
            key={t.id}
            data-testid={`profile-detail-tab-${t.id}`}
            variant={tab === t.id ? "primary" : "ghost"}
            size="sm"
            aria-pressed={tab === t.id}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </Button>
        ))}
      </nav>

      {tab === "datasets" && (
        <Card data-testid="profile-detail-datasets-panel">
          <a
            href={`/profiles/${profile}/datasets/recognition`}
            data-testid="profile-detail-datasets-link"
          >
            Open the dataset kanban
          </a>
        </Card>
      )}
      {tab === "runs" && (
        <Card data-testid="profile-detail-runs-panel">
          <p>Training runs land in a later milestone.</p>
        </Card>
      )}
      {tab === "models" && (
        <Card data-testid="profile-detail-models-panel">
          <p>The model registry lands in a later milestone.</p>
        </Card>
      )}

      {tab === "defaults" && (
        <Card data-testid="profile-detail-defaults-panel">
          <div data-testid="profile-detail-defaults-task-tabs">
            <Button
              data-testid="profile-detail-defaults-task-detection"
              variant={task === "detection" ? "primary" : "ghost"}
              size="sm"
              aria-pressed={task === "detection"}
              onClick={() => setTask("detection")}
            >
              Detection
            </Button>
            <Button
              data-testid="profile-detail-defaults-task-recognition"
              variant={task === "recognition" ? "primary" : "ghost"}
              size="sm"
              aria-pressed={task === "recognition"}
              onClick={() => setTask("recognition")}
            >
              Recognition
            </Button>
          </div>

          <p data-testid="profile-detail-defaults-source">
            {saved
              ? "Showing this profile's saved defaults."
              : "No saved defaults — showing the seed."}
          </p>

          {error && (
            <p data-testid="profile-detail-defaults-error" role="alert">
              {error}
            </p>
          )}
          {loading && (
            <p data-testid="profile-detail-defaults-loading">Loading…</p>
          )}

          {args && (
            <RunArgsEditor
              task={task}
              value={args}
              onChange={setArgs}
              testIdPrefix="profile-detail-defaults"
              disabled={busy}
            />
          )}

          <footer
            style={{ display: "flex", gap: "1rem", alignItems: "center" }}
          >
            <Button
              data-testid="profile-detail-defaults-save"
              disabled={busy || !args}
              onClick={() => void handleSave()}
            >
              {busy ? "Saving…" : "Save defaults"}
            </Button>
            <Button
              data-testid="profile-detail-defaults-reset"
              variant="ghost"
              disabled={busy}
              onClick={() => void handleReset()}
            >
              Reset to seed
            </Button>
            {status && (
              <span data-testid="profile-detail-defaults-status">{status}</span>
            )}
          </footer>
        </Card>
      )}
    </div>
  );
}
