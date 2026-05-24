// REST client for the /api/profiles/{profile}/datasets surface (spec 05).

import { ApiError } from "./profiles";

export type KanbanColumnId = "unassigned" | "train" | "val";

export interface KanbanPageChip {
  key: string;
  page_name: string;
  crop_name: string | null;
  label_text: string | null;
  is_changed: boolean;
  change_summary: string | null;
}

export interface KanbanProjectRow {
  project_id: string;
  source: "pending" | "on_disk";
  page_count: number;
  is_changed: boolean;
  style_tags: string[];
  pages: KanbanPageChip[];
}

export interface KanbanColumn {
  rows: KanbanProjectRow[];
}

export interface KanbanView {
  profile: string;
  task: string;
  columns: Record<KanbanColumnId, KanbanColumn>;
  include_detection: boolean;
  include_recognition: boolean;
}

export interface AssignmentEntry {
  key: string;
  target_split: KanbanColumnId;
}

export interface ApplyAssignmentRequest {
  assignments: AssignmentEntry[];
}

export interface ApplyError {
  key: string;
  error: string;
}

export interface ApplyResult {
  view: KanbanView;
  errors: ApplyError[];
}

function datasetsBase(profile: string, task: string): string {
  return `/api/profiles/${encodeURIComponent(profile)}/datasets/${encodeURIComponent(task)}`;
}

async function jsonRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
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

export function fetchKanban(
  profile: string,
  task: string,
): Promise<KanbanView> {
  return jsonRequest<KanbanView>(`${datasetsBase(profile, task)}/kanban`);
}

export function scanKanban(profile: string, task: string): Promise<KanbanView> {
  return jsonRequest<KanbanView>(`${datasetsBase(profile, task)}/scan`, {
    method: "POST",
  });
}

export function setIncludeToggles(
  profile: string,
  task: string,
  includeDetection: boolean,
  includeRecognition: boolean,
): Promise<KanbanView> {
  return jsonRequest<KanbanView>(
    `${datasetsBase(profile, task)}/include-toggles`,
    {
      method: "POST",
      body: JSON.stringify({
        include_detection: includeDetection,
        include_recognition: includeRecognition,
      }),
    },
  );
}

export async function applyAssignments(
  profile: string,
  task: string,
  request: ApplyAssignmentRequest,
): Promise<ApplyResult> {
  const resp = await fetch(`${datasetsBase(profile, task)}/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  const body = (await resp.json()) as unknown;
  if (!resp.ok) {
    const envelope = body as { code?: string; message?: string };
    throw new ApiError(
      envelope.code ?? "unknown",
      envelope.message ?? resp.statusText,
      resp.status,
    );
  }
  const header = resp.headers.get("X-Apply-Errors");
  const errors = header ? (JSON.parse(header) as ApplyError[]) : [];
  return { view: body as KanbanView, errors };
}
