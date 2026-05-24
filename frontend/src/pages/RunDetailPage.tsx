// RunDetailPage — run monitor: status, progress, log stream, loss chart
// (spec 06 §7, route /runs/:runId).

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { Badge, Button, Card } from "@concavetrillion/pd-ui/primitives";
import { cancelRun, fetchRun, fetchRunProgress } from "../api/runs";
import type { Run } from "../api/runs";
import { subscribeToJob } from "../api/jobs";
import type { JobEvent } from "../api/jobs";
import { LogViewer } from "../components/LogViewer";
import { LossChart } from "../components/LossChart";
import type { MetricPoint } from "../components/LossChart";

const TERMINAL = new Set(["succeeded", "failed", "cancelled"]);

export function RunDetailPage(): JSX.Element {
  const { runId = "" } = useParams<{ runId: string }>();
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stdout, setStdout] = useState<string[]>([]);
  const [metrics, setMetrics] = useState<MetricPoint[]>([]);
  const [progress, setProgress] = useState<{ current: number; total: number }>({
    current: 0,
    total: 0,
  });
  const stepRef = useRef(0);

  const load = useCallback(async () => {
    try {
      const r = await fetchRun(runId);
      setRun(r);
      setError(null);
      // Replay persisted progress for a finished or reloaded run (spec 06 §4).
      const replay = await fetchRunProgress(runId);
      const pts: MetricPoint[] = [];
      for (const rec of replay.records) {
        if (rec.type === "metric" && typeof rec.value === "number") {
          pts.push({ step: pts.length + 1, value: rec.value });
        }
        if (rec.type === "progress") {
          setProgress({
            current: Number(rec.current ?? 0),
            total: Number(rec.total ?? 0),
          });
        }
      }
      if (pts.length > 0) {
        setMetrics(pts);
        stepRef.current = pts.length;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load run");
    }
  }, [runId]);

  useEffect(() => {
    void load();
  }, [load]);

  // Live SSE: stream the owning job while the run is non-terminal.
  useEffect(() => {
    if (!run || run.job_id === null || TERMINAL.has(run.status)) return;
    const sub = subscribeToJob(run.job_id, {
      onEvent: (event: JobEvent) => {
        if (event.kind === "log") {
          const line = String(
            event.payload.line ?? event.payload.message ?? "",
          );
          if (line) setStdout((prev) => [...prev, line]);
        }
        if (event.kind === "progress") {
          setProgress({
            current: Number(event.payload.current ?? 0),
            total: Number(event.payload.total ?? 0),
          });
        }
        if (event.kind === "metric") {
          const value = event.payload.value;
          if (typeof value === "number") {
            stepRef.current += 1;
            setMetrics((prev) => [...prev, { step: stepRef.current, value }]);
          }
        }
      },
      onClose: () => {
        void load();
      },
    });
    return () => sub.close();
  }, [run, load]);

  const handleCancel = async () => {
    try {
      const updated = await cancelRun(runId);
      setRun(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cancel failed");
    }
  };

  if (error) {
    return (
      <div data-testid="run-detail-page">
        <p data-testid="run-detail-error" role="alert">
          {error}
        </p>
      </div>
    );
  }
  if (!run) {
    return (
      <div data-testid="run-detail-page">
        <p data-testid="run-detail-loading">Loading…</p>
      </div>
    );
  }

  const pct =
    progress.total > 0
      ? Math.round((progress.current / progress.total) * 100)
      : 0;

  return (
    <div data-testid="run-detail-page">
      <header>
        <h1>{run.model_name}</h1>
        <Badge data-testid="run-detail-status-badge">{run.status}</Badge>
      </header>

      <progress data-testid="run-detail-progress-bar" max={100} value={pct} />

      <div style={{ display: "flex", gap: "0.5rem" }}>
        {run.status === "running" && (
          <Button
            data-testid="run-detail-cancel"
            onClick={() => void handleCancel()}
          >
            Cancel
          </Button>
        )}
        {run.status === "succeeded" && (
          <Button
            data-testid="run-detail-open-model"
            variant="ghost"
            onClick={() => {
              window.location.href = `/models/${encodeURIComponent(run.model_name)}`;
            }}
          >
            Open Model
          </Button>
        )}
        <Button
          data-testid="run-detail-open-eval"
          variant="ghost"
          onClick={() => {
            window.location.href = `/eval?model=${encodeURIComponent(run.model_name)}`;
          }}
        >
          Open Eval
        </Button>
      </div>

      <Card>
        <h2>Args</h2>
        <pre data-testid="run-detail-args-summary">
          {JSON.stringify(run.args, null, 2)}
        </pre>
      </Card>

      <Card>
        <LossChart series={metrics} label="val_cer" />
      </Card>

      <LogViewer stdout={stdout} stderr={[]} />
    </div>
  );
}
