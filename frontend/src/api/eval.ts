// REST client for the /api/eval surface (spec 07-evaluation-and-metrics).

import { ApiError } from "./profiles";

export interface EvalMetrics {
  cer: number | null;
  wer: number | null;
  exact_match_rate: number | null;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  iou_50: number | null;
  iou_50_95: number | null;
  accuracy: number | null;
  f1_macro: number | null;
  per_class: Record<string, ClassMetrics> | null;
}

export interface ClassMetrics {
  n: number;
  precision: number;
  recall: number;
  f1: number;
}

export interface EvalSlice {
  feature: string;
  n_pos: number;
  n_neg: number;
  n_excluded: number;
  cer_pos: number | null;
  cer_neg: number | null;
  wer_pos: number | null;
  wer_neg: number | null;
  delta_cer: number | null;
  low_support: boolean;
}

export interface EvalResult {
  run_id: string;
  profile: string;
  task: string;
  model_name: string;
  val_source: string;
  overall: EvalMetrics;
  slices: EvalSlice[];
  sample_count: number;
  excluded_count: number;
  duration_seconds: number;
  finished_at: string;
}

export interface EvalRequestPayload {
  profile: string;
  task: string;
  model_name: string;
  val_source?: string | null;
  persist_predictions?: boolean;
  slice_glyph_features?: boolean;
  notes?: string | null;
}

export interface EvalResponse {
  run_id: string;
  job_id: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (resp.status === 204) {
    return undefined as T;
  }
  const body = (await resp.json()) as unknown;
  if (!resp.ok) {
    const envelope = body as { code?: string; message?: string };
    throw new ApiError(
      envelope.code ?? "unknown",
      envelope.message ?? resp.statusText,
      resp.status,
    );
  }
  return body as T;
}

export function submitEval(payload: EvalRequestPayload): Promise<EvalResponse> {
  return request<EvalResponse>("/api/eval", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchEvalResult(runId: string): Promise<EvalResult> {
  return request<EvalResult>(
    `/api/eval/${encodeURIComponent(runId)}/result`,
  );
}
