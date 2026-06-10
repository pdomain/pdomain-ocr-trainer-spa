// REST client for the /api/models surface (spec 08-models).

import { ApiError } from "./profiles";

export interface ModelPaths {
  weights: string;
  sidecar: string;
  config: string | null;
}

export interface TrainedOnSource {
  repo: string;
  revision: string | null;
  rows: number | null;
  weight: number;
  source: string;
}

export interface SidecarEvalSummary {
  best_run_id: string;
  overall: Record<string, number>;
}

export interface ModelSidecar {
  name: string;
  task: string;
  language: string | null;
  typeface: string | null;
  doctr_arch: string | null;
  trainer_version: string | null;
  trained_at: string | null;
  trained_on: TrainedOnSource[];
  args: Record<string, unknown>;
  qualifier: string | null;
  eval: SidecarEvalSummary | null;
}

export interface TrainedModel {
  name: string;
  profile: string;
  task: string;
  language: string | null;
  typeface: string | null;
  paths: ModelPaths;
  sidecar: ModelSidecar;
  published_to: unknown[];
}

export interface ModelListItem {
  model: TrainedModel;
  has_sidecar: boolean;
  is_legacy: boolean;
}

export interface ModelListResponse {
  models: ModelListItem[];
}

export interface PatchModelPayload {
  language?: string | null;
  typeface?: string | null;
  qualifier?: string | null;
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

export function fetchModels(params?: {
  profile?: string;
  task?: string;
  includeLegacy?: boolean;
}): Promise<ModelListResponse> {
  const qs = new URLSearchParams();
  if (params?.profile) qs.set("profile", params.profile);
  if (params?.task) qs.set("task", params.task);
  if (params?.includeLegacy === false) qs.set("include_legacy", "false");
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request<ModelListResponse>(`/api/models${suffix}`);
}

export function fetchModel(name: string): Promise<ModelListItem> {
  return request<ModelListItem>(`/api/models/${encodeURIComponent(name)}`);
}

export function regenerateSidecar(name: string): Promise<ModelListItem> {
  return request<ModelListItem>(
    `/api/models/${encodeURIComponent(name)}/regenerate-sidecar`,
    { method: "POST" },
  );
}

export function patchModel(
  name: string,
  payload: PatchModelPayload,
): Promise<ModelListItem> {
  return request<ModelListItem>(`/api/models/${encodeURIComponent(name)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function renameModel(
  name: string,
  newName: string,
): Promise<ModelListItem> {
  return request<ModelListItem>(
    `/api/models/${encodeURIComponent(name)}/rename`,
    { method: "POST", body: JSON.stringify({ new_name: newName }) },
  );
}

export function deleteModel(name: string): Promise<void> {
  return request<undefined>(`/api/models/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
}
