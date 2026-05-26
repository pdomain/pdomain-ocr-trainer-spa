// ModelDetailPage — sidecar viewer + rename / delete / regenerate (spec 08 §7).

import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button, Card } from "@pdomain/pdomain-ui/primitives";
import {
  fetchModel,
  regenerateSidecar,
  renameModel,
  deleteModel,
} from "../api/models";
import type { ModelListItem } from "../api/models";
import { ApiError } from "../api/profiles";

export function ModelDetailPage(): JSX.Element {
  const { name = "" } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const [item, setItem] = useState<ModelListItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [renaming, setRenaming] = useState(false);
  const [newName, setNewName] = useState("");

  const load = useCallback(async () => {
    try {
      setItem(await fetchModel(name));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load model");
    }
  }, [name]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleRegenerate = async () => {
    try {
      setItem(await regenerateSidecar(name));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Regenerate failed");
    }
  };

  const handleRename = async () => {
    try {
      const updated = await renameModel(name, newName);
      setRenaming(false);
      navigate(`/models/${encodeURIComponent(updated.model.name)}`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Rename failed",
      );
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete model ${name}?`)) return;
    try {
      await deleteModel(name);
      navigate("/models");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  if (error && !item) {
    return (
      <div data-testid="models-detail-page">
        <p data-testid="models-detail-error" role="alert">
          {error}
        </p>
      </div>
    );
  }

  if (!item) {
    return (
      <div data-testid="models-detail-page">
        <p data-testid="models-detail-loading">Loading…</p>
      </div>
    );
  }

  const { model, has_sidecar } = item;
  const evalSummary = model.sidecar.eval;

  return (
    <div data-testid="models-detail-page">
      <header>
        <h1>{model.name}</h1>
        <p>
          Profile: {model.profile} · Task: {model.task}
        </p>
        <p>
          Language: {model.language ?? "—"} · Typeface: {model.typeface ?? "—"}
        </p>
      </header>

      {error && (
        <p data-testid="models-detail-error" role="alert">
          {error}
        </p>
      )}

      <div style={{ display: "flex", gap: "0.5rem" }}>
        <a
          href={`/eval?model=${encodeURIComponent(model.name)}`}
          data-testid="models-detail-open-eval"
        >
          Open Eval
        </a>
        <Button
          data-testid="models-detail-rename"
          onClick={() => {
            setNewName(model.name);
            setRenaming(true);
          }}
        >
          Rename
        </Button>
        <Button
          data-testid="models-detail-delete"
          variant="danger"
          onClick={() => void handleDelete()}
        >
          Delete
        </Button>
      </div>

      {!has_sidecar && (
        <Card>
          <p data-testid="models-detail-sidecar-missing">
            Sidecar missing — regenerate?
          </p>
          <Button
            data-testid="models-detail-regenerate"
            onClick={() => void handleRegenerate()}
          >
            Regenerate sidecar
          </Button>
        </Card>
      )}

      {renaming && (
        <Card>
          <div data-testid="models-detail-rename-dialog">
            <label>
              New name
              <input
                data-testid="models-detail-rename-input"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </label>
            <Button
              data-testid="models-detail-rename-submit"
              onClick={() => void handleRename()}
            >
              Rename
            </Button>
            <Button variant="ghost" onClick={() => setRenaming(false)}>
              Cancel
            </Button>
          </div>
        </Card>
      )}

      <Card>
        <h2>Sidecar</h2>
        <pre data-testid="models-detail-sidecar-json">
          {JSON.stringify(model.sidecar, null, 2)}
        </pre>
      </Card>

      {evalSummary && (
        <Card>
          <h2>Best Eval</h2>
          <p data-testid="models-detail-eval-summary">
            <a
              href={`/eval/${encodeURIComponent(evalSummary.best_run_id)}/result`}
            >
              {evalSummary.best_run_id}
            </a>{" "}
            — {JSON.stringify(evalSummary.overall)}
          </p>
        </Card>
      )}

      <Card>
        <h2>Trained from</h2>
        <ul data-testid="models-detail-trained-on">
          {model.sidecar.trained_on.map((src) => (
            <li key={src.repo}>
              {src.repo} (rev {src.revision ?? "—"}, {src.rows ?? "?"} rows,
              weight {src.weight})
            </li>
          ))}
          {model.sidecar.trained_on.length === 0 && <li>—</li>}
        </ul>
      </Card>
    </div>
  );
}
