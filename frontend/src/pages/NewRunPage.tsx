// NewRunPage — the training-run creation form (spec 06 §2, route /runs/new).
//
// Composes the RunArgsEditor (prefilled from the profile's saved
// training-defaults, or the seed) with a profile + task selector. Submitting
// POSTs /api/runs and navigates to the new run-detail page.

import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button, Card } from "@concavetrillion/pd-ui/primitives";
import { RunArgsEditor } from "../components/RunArgsEditor";
import { fetchProfiles, fetchTrainingDefaultsOrSeed } from "../api/profiles";
import type { Profile, TrainingArgs } from "../api/profiles";
import { createRun } from "../api/runs";
import { ApiError } from "../api/profiles";

const TASKS = ["detection", "recognition"] as const;

export function NewRunPage(): JSX.Element {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [profile, setProfile] = useState(params.get("profile") ?? "");
  const [task, setTask] = useState<string>(params.get("task") ?? "recognition");
  const [args, setArgs] = useState<TrainingArgs>({});
  const [qualifier, setQualifier] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    void fetchProfiles().then((resp) => {
      setProfiles(resp.profiles);
      if (profile === "" && resp.profiles.length > 0) {
        setProfile(resp.profiles[0].name);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadArgs = useCallback(async () => {
    if (profile === "") return;
    try {
      const { args: resolved } = await fetchTrainingDefaultsOrSeed(
        profile,
        task,
      );
      setArgs(resolved);
    } catch {
      setArgs({});
    }
  }, [profile, task]);

  useEffect(() => {
    void loadArgs();
  }, [loadArgs]);

  const handleStart = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const resp = await createRun({
        profile,
        task,
        args,
        qualifier: qualifier || null,
      });
      navigate(`/runs/${resp.run_id}`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Failed to start run",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div data-testid="new-run-page">
      <h1>New training run</h1>

      {error && (
        <p data-testid="new-run-error" role="alert">
          {error}
        </p>
      )}

      <Card>
        <label>
          Profile
          <select
            data-testid="new-run-profile"
            value={profile}
            onChange={(e) => setProfile(e.target.value)}
          >
            {profiles.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Task
          <select
            data-testid="new-run-task"
            value={task}
            onChange={(e) => setTask(e.target.value)}
          >
            {TASKS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>

        <label>
          Model-name qualifier (optional)
          <input
            data-testid="new-run-qualifier"
            value={qualifier}
            onChange={(e) => setQualifier(e.target.value)}
          />
        </label>
      </Card>

      <Card>
        <RunArgsEditor
          task={task}
          value={args}
          onChange={setArgs}
          testIdPrefix="new-run-args"
        />
      </Card>

      <Button
        data-testid="new-run-start"
        disabled={submitting || profile === ""}
        onClick={() => void handleStart()}
      >
        {submitting ? "Starting…" : "Start run"}
      </Button>
    </div>
  );
}
