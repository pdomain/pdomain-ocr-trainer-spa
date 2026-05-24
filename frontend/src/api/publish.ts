// REST client for the /api/publish surface (spec 09 §5–§6, M11).

import { ApiError } from "./profiles";

export interface PublishDatasetPayload {
  profile: string;
  task: string;
  repo: string;
  visibility: "private" | "public";
  qualifier?: string | null;
  license: string;
  notes?: string | null;
}

export interface PublishModelPayload {
  model_name: string;
  repo: string;
  visibility: "private" | "public";
  notes?: string | null;
}

export interface PublishResponse {
  run_id: string;
  job_id: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    let message = `HTTP ${resp.status}`;
    let code: string | undefined;
    try {
      const body = (await resp.json()) as {
        detail?: string;
        message?: string;
        code?: string;
      };
      message = body.message ?? body.detail ?? message;
      code = body.code;
    } catch {
      // ignore parse errors
    }
    throw new ApiError(code ?? "unknown", message, resp.status);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export function publishDataset(
  payload: PublishDatasetPayload,
): Promise<PublishResponse> {
  return request<PublishResponse>("/api/publish/dataset", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function publishModel(
  payload: PublishModelPayload,
): Promise<PublishResponse> {
  return request<PublishResponse>("/api/publish/model", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
