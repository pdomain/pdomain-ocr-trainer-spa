// EvalResultPage — renders a finished eval's metrics (spec 07 §6.2,
// route /eval/:runId/result).

import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Button, Card } from "@pdomain/pdomain-ui/primitives";
import { fetchEvalResult } from "../api/eval";
import type { EvalResult } from "../api/eval";
import { EvalMetricsTable } from "../components/EvalMetricsTable";

export function EvalResultPage(): React.JSX.Element {
  const { runId = "" } = useParams<{ runId: string }>();
  const [result, setResult] = useState<EvalResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    try {
      setResult(await fetchEvalResult(runId));
      setError(null);
      setPending(false);
    } catch (err) {
      const code =
        err && typeof err === "object" && "status" in err
          ? (err as { status: number }).status
          : 0;
      if (code === 404) {
        setPending(true);
        setError(null);
      } else {
        setError(err instanceof Error ? err.message : "Failed to load result");
      }
    }
  }, [runId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) {
    return (
      <div data-testid="eval-result-page">
        <p data-testid="eval-result-error" role="alert">
          {error}
        </p>
      </div>
    );
  }

  if (pending) {
    return (
      <div data-testid="eval-result-page">
        <p data-testid="eval-result-pending">Eval has not finished yet.</p>
        <Button data-testid="eval-result-refresh" onClick={() => void load()}>
          Refresh
        </Button>
      </div>
    );
  }

  if (!result) {
    return (
      <div data-testid="eval-result-page">
        <p data-testid="eval-result-loading">Loading…</p>
      </div>
    );
  }

  return (
    <div data-testid="eval-result-page">
      <header>
        <h1>Eval result</h1>
        <p>
          {result.profile} · {result.task} · {result.model_name}
        </p>
        <p>
          N {result.sample_count} · {result.duration_seconds.toFixed(1)}s
        </p>
      </header>

      <Card>
        <EvalMetricsTable overall={result.overall} slices={result.slices} />
      </Card>

      <div style={{ display: "flex", gap: "0.5rem" }}>
        <a
          href={`/api/eval/${encodeURIComponent(runId)}/result`}
          data-testid="eval-result-download-json"
        >
          Download JSON
        </a>
        <a
          href={`/api/eval/${encodeURIComponent(runId)}/result.md`}
          data-testid="eval-result-download-md"
        >
          Download Markdown
        </a>
      </div>
    </div>
  );
}
