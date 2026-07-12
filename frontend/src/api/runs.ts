// REST client for the /api/runs surface (spec 06-training-runs).

import { ApiError } from "./profiles";
import type { TrainingArgs } from "./profiles";

export type RunStatus =
  "pending" | "running" | "succeeded" | "failed" | "cancelled";

export type RunKind = "train" | "eval" | "publish-dataset" | "publish-model";

/** A training/eval/publish run (GET /api/runs/{run_id}). */
export interface Run {
  id: string;
  profile: string;
  task: string;
  kind: RunKind;
  status: RunStatus;
  model_name: string;
  args: TrainingArgs;
  notes: string | null;
  device: number | null;
  seed: number | null;
  started_at: string;
  finished_at: string | null;
  exit_code: number | null;
  artefact_paths: string[];
  job_id: string | null;
}

export interface RunListResponse {
  runs: Run[];
}

export interface CreateRunPayload {
  profile: string;
  task: string;
  args?: TrainingArgs;
  notes?: string | null;
  device?: number | null;
  seed?: number | null;
  model_name?: string | null;
  qualifier?: string | null;
}

export interface CreateRunResponse {
  run_id: string;
  job_id: string;
}

/** One progress.jsonl record for chart replay (GET /api/runs/{id}/progress). */
export interface ProgressRecord {
  t: number;
  type: "progress" | "metric";
  seq?: number;
  [key: string]: unknown;
}

export interface ProgressResponse {
  records: ProgressRecord[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    ...init,
    // eslint-disable-next-line @typescript-eslint/no-misused-spread -- HeadersInit is always Record<string,string> at internal call-sites; Headers instance never passed
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

export function fetchRuns(): Promise<RunListResponse> {
  return request<RunListResponse>("/api/runs");
}

export function fetchRun(runId: string): Promise<Run> {
  return request<Run>(`/api/runs/${encodeURIComponent(runId)}`);
}

export function createRun(
  payload: CreateRunPayload,
): Promise<CreateRunResponse> {
  return request<CreateRunResponse>("/api/runs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function cancelRun(runId: string): Promise<Run> {
  return request<Run>(`/api/runs/${encodeURIComponent(runId)}/cancel`, {
    method: "POST",
  });
}

export function deleteRun(runId: string): Promise<void> {
  return request<undefined>(`/api/runs/${encodeURIComponent(runId)}`, {
    method: "DELETE",
  });
}

export function fetchRunProgress(runId: string): Promise<ProgressResponse> {
  return request<ProgressResponse>(
    `/api/runs/${encodeURIComponent(runId)}/progress`,
  );
}
