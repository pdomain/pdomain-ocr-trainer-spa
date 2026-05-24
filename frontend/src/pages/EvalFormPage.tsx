// EvalFormPage — the eval-submission form (spec 07 §6.1, route /eval).

import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button, Card } from "@concavetrillion/pd-ui/primitives";
import { fetchProfiles } from "../api/profiles";
import type { Profile } from "../api/profiles";
import { fetchModels } from "../api/models";
import type { ModelListItem } from "../api/models";
import { submitEval } from "../api/eval";
import { ApiError } from "../api/profiles";

const TASKS = ["detection", "recognition"] as const;

export function EvalFormPage(): JSX.Element {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [models, setModels] = useState<ModelListItem[]>([]);
  const [profile, setProfile] = useState(params.get("profile") ?? "");
  const [task, setTask] = useState<string>("recognition");
  const [modelName, setModelName] = useState(params.get("model") ?? "");
  const [valSource, setValSource] = useState("local");
  const [sliceGlyph, setSliceGlyph] = useState(false);
  const [persistPred, setPersistPred] = useState(false);
  const [showAll, setShowAll] = useState(false);
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

  const loadModels = useCallback(async () => {
    try {
      const resp = await fetchModels(showAll ? {} : { profile, task });
      setModels(resp.models);
    } catch {
      setModels([]);
    }
  }, [profile, task, showAll]);

  useEffect(() => {
    void loadModels();
  }, [loadModels]);

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const resp = await submitEval({
        profile,
        task,
        model_name: modelName,
        val_source: valSource === "local" ? null : valSource,
        slice_glyph_features: sliceGlyph,
        persist_predictions: persistPred,
      });
      navigate(`/runs/${resp.run_id}`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Failed to start eval",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div data-testid="eval-form-page">
      <h1>Evaluate a model</h1>

      {error && (
        <p data-testid="eval-form-error" role="alert">
          {error}
        </p>
      )}

      <Card>
        <label>
          Profile
          <select
            data-testid="eval-form-profile"
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

        <fieldset>
          <legend>Task</legend>
          {TASKS.map((t) => (
            <label key={t}>
              <input
                type="radio"
                name="eval-task"
                data-testid={`eval-form-task-${t}`}
                checked={task === t}
                onChange={() => setTask(t)}
              />
              {t}
            </label>
          ))}
        </fieldset>

        <label>
          Model
          <select
            data-testid="eval-form-model"
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
          >
            <option value="">— select a model —</option>
            {models.map((m) => (
              <option key={m.model.name} value={m.model.name}>
                {m.model.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <input
            type="checkbox"
            data-testid="eval-form-show-all-models"
            checked={showAll}
            onChange={(e) => setShowAll(e.target.checked)}
          />
          Show all models
        </label>

        <fieldset>
          <legend>Validation source</legend>
          <label>
            <input
              type="radio"
              name="eval-source"
              data-testid="eval-form-source-local"
              checked={valSource === "local"}
              onChange={() => setValSource("local")}
            />
            Local
          </label>
          <label>
            <input
              type="radio"
              name="eval-source"
              data-testid="eval-form-source-custom"
              checked={valSource !== "local"}
              onChange={() => setValSource("custom:")}
            />
            Custom path
          </label>
          {valSource !== "local" && (
            <input
              data-testid="eval-form-source-custom-path"
              placeholder="path or hf:repo@rev"
              value={valSource}
              onChange={(e) => setValSource(e.target.value)}
            />
          )}
        </fieldset>

        {task === "recognition" && (
          <>
            <label>
              <input
                type="checkbox"
                data-testid="eval-form-slice-glyph-features"
                checked={sliceGlyph}
                onChange={(e) => setSliceGlyph(e.target.checked)}
              />
              Slice by glyph annotations
            </label>
            <label>
              <input
                type="checkbox"
                data-testid="eval-form-persist-predictions"
                checked={persistPred}
                onChange={(e) => setPersistPred(e.target.checked)}
              />
              Persist per-prediction details
            </label>
          </>
        )}
      </Card>

      <Button
        data-testid="eval-form-submit"
        disabled={submitting || profile === "" || modelName === ""}
        onClick={() => void handleSubmit()}
      >
        {submitting ? "Starting…" : "Run eval"}
      </Button>
    </div>
  );
}
