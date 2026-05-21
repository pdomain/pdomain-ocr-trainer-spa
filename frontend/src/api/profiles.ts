// REST client for the /api/profiles surface (spec 04).

export const TYPEFACE_VALUES = [
  "roman",
  "italic",
  "smallcaps",
  "blackletter",
  "fraktur",
  "clogaelach",
  "greek",
  "greek-classical",
  "typeface",
] as const;

export type Typeface = (typeof TYPEFACE_VALUES)[number];

export interface ProfileCounts {
  detection_train_pages: number;
  detection_val_pages: number;
  recognition_train_crops: number;
  recognition_val_crops: number;
  typeface_train_crops: number;
  typeface_val_crops: number;
  glyph_train_crops: number;
  glyph_val_crops: number;
}

export interface Profile {
  name: string;
  display_name: string;
  language: string | null;
  typeface: Typeface | null;
  is_base: boolean;
  has_training_data: boolean;
  has_validation_data: boolean;
  counts: ProfileCounts;
}

export interface ProfileListResponse {
  profiles: Profile[];
  has_legacy_layout: boolean;
}

export interface CreateProfilePayload {
  name: string;
  display_name?: string | null;
  language?: string | null;
  typeface?: Typeface | null;
  notes?: string | null;
}

export type UpdateProfilePayload = Omit<CreateProfilePayload, "name">;

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
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

export function fetchProfiles(): Promise<ProfileListResponse> {
  return request<ProfileListResponse>("/api/profiles");
}

export function createProfile(payload: CreateProfilePayload): Promise<Profile> {
  return request<Profile>("/api/profiles", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateProfile(
  name: string,
  payload: UpdateProfilePayload,
): Promise<Profile> {
  return request<Profile>(`/api/profiles/${encodeURIComponent(name)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteProfile(name: string): Promise<void> {
  return request<void>(`/api/profiles/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
}

export function migrateLegacy(): Promise<void> {
  return request<void>("/api/profiles/migrate-legacy", { method: "POST" });
}
