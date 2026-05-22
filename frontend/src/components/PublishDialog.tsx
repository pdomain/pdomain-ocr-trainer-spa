// PublishDialog — modal for publishing a dataset or model to HuggingFace.
// Spec: 09-hf-integration §5–§6, M11.

import { useState } from "react";
import { Button } from "@concavetrillion/pd-ui/primitives";
import type { PublishDatasetPayload, PublishModelPayload } from "../api/publish";
import { publishDataset, publishModel } from "../api/publish";

type PublishMode = "dataset" | "model";

export interface PublishDialogProps {
  mode: PublishMode;
  /** profile name — required for dataset publish */
  profile?: string;
  /** task — required for dataset publish */
  task?: string;
  /** model_name — required for model publish */
  modelName?: string;
  /** suggested repo (owner/name) */
  defaultRepo?: string;
  onClose: () => void;
  onSuccess: (runId: string, jobId: string) => void;
}

const COMMON_LICENSES = [
  "apache-2.0",
  "mit",
  "cc-by-4.0",
  "cc-by-sa-4.0",
  "cc-by-nc-4.0",
  "cc0-1.0",
  "gpl-3.0",
  "gpl-3.0-only",
] as const;

export function PublishDialog({
  mode,
  profile,
  task,
  modelName,
  defaultRepo = "",
  onClose,
  onSuccess,
}: PublishDialogProps): JSX.Element {
  const [repo, setRepo] = useState(defaultRepo);
  const [visibility, setVisibility] = useState<"private" | "public">("private");
  const [license, setLicense] = useState("apache-2.0");
  const [customLicense, setCustomLicense] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const effectiveLicense =
    license === "__custom__" ? customLicense.trim() : license;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      if (mode === "dataset") {
        const payload: PublishDatasetPayload = {
          profile: profile ?? "",
          task: task ?? "",
          repo,
          visibility,
          license: effectiveLicense,
          notes: notes.trim() || null,
        };
        const result = await publishDataset(payload);
        onSuccess(result.run_id, result.job_id);
      } else {
        const payload: PublishModelPayload = {
          model_name: modelName ?? "",
          repo,
          visibility,
          notes: notes.trim() || null,
        };
        const result = await publishModel(payload);
        onSuccess(result.run_id, result.job_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Publish failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="publish-dialog-title"
      data-testid="publish-dialog"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        style={{
          background: "var(--color-surface, #fff)",
          borderRadius: "8px",
          padding: "1.5rem",
          minWidth: "400px",
          maxWidth: "560px",
          width: "100%",
        }}
      >
        <h2 id="publish-dialog-title" style={{ marginTop: 0 }}>
          {mode === "dataset" ? "Publish Dataset" : "Publish Model"} to HuggingFace
        </h2>

        {error && (
          <div
            role="alert"
            data-testid="publish-dialog-error"
            style={{ color: "var(--color-error, red)", marginBottom: "1rem" }}
          >
            {error}
          </div>
        )}

        <form onSubmit={(e) => void handleSubmit(e)}>
          <div style={{ marginBottom: "0.75rem" }}>
            <label htmlFor="publish-repo">
              <strong>Repository</strong> (owner/name)
            </label>
            <input
              id="publish-repo"
              data-testid="publish-repo-input"
              type="text"
              required
              placeholder="owner/dataset-name"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              style={{ display: "block", width: "100%", marginTop: "0.25rem" }}
            />
          </div>

          <div style={{ marginBottom: "0.75rem" }}>
            <label htmlFor="publish-visibility">
              <strong>Visibility</strong>
            </label>
            <select
              id="publish-visibility"
              data-testid="publish-visibility-select"
              value={visibility}
              onChange={(e) =>
                setVisibility(e.target.value as "private" | "public")
              }
              style={{ display: "block", width: "100%", marginTop: "0.25rem" }}
            >
              <option value="private">Private</option>
              <option value="public">Public</option>
            </select>
          </div>

          {mode === "dataset" && (
            <>
              <div style={{ marginBottom: "0.75rem" }}>
                <label htmlFor="publish-license">
                  <strong>License</strong> (SPDX)
                </label>
                <select
                  id="publish-license"
                  data-testid="publish-license-select"
                  value={license}
                  onChange={(e) => setLicense(e.target.value)}
                  style={{
                    display: "block",
                    width: "100%",
                    marginTop: "0.25rem",
                  }}
                >
                  {COMMON_LICENSES.map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                  <option value="__custom__">Other (type below)…</option>
                </select>
              </div>

              {license === "__custom__" && (
                <div style={{ marginBottom: "0.75rem" }}>
                  <label htmlFor="publish-license-custom">
                    <strong>Custom SPDX license identifier</strong>
                  </label>
                  <input
                    id="publish-license-custom"
                    data-testid="publish-license-custom-input"
                    type="text"
                    required
                    placeholder="e.g. bsd-3-clause"
                    value={customLicense}
                    onChange={(e) => setCustomLicense(e.target.value)}
                    style={{
                      display: "block",
                      width: "100%",
                      marginTop: "0.25rem",
                    }}
                  />
                </div>
              )}
            </>
          )}

          <div style={{ marginBottom: "1rem" }}>
            <label htmlFor="publish-notes">
              <strong>Notes</strong> (optional)
            </label>
            <textarea
              id="publish-notes"
              data-testid="publish-notes-textarea"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              style={{ display: "block", width: "100%", marginTop: "0.25rem" }}
            />
          </div>

          <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
            <Button
              type="button"
              variant="ghost"
              data-testid="publish-dialog-cancel"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              data-testid="publish-dialog-submit"
              disabled={submitting}
            >
              {submitting ? "Publishing…" : "Publish"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
