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
  return request<undefined>(`/api/profiles/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
}

export function migrateLegacy(): Promise<void> {
  return request<undefined>("/api/profiles/migrate-legacy", { method: "POST" });
}

// --- training-config defaults (spec 04 §3.3) -------------------------------

// The run-form args dict is task-shaped and free-form — see spec 04 §3.2.
export type TrainingArgs = Record<string, unknown>;

export interface TrainingDefaultsResponse {
  task: string;
  args: TrainingArgs;
}

export function fetchTrainingDefaultsSeed(
  profile: string,
  task: string,
): Promise<TrainingDefaultsResponse> {
  return request<TrainingDefaultsResponse>(
    `/api/profiles/${encodeURIComponent(profile)}/training-defaults/${encodeURIComponent(task)}/seed`,
  );
}

// Resolves to the saved defaults, or the seed when nothing has been saved yet
// (the GET 404s — spec 04 §3.3). The boolean `saved` flag tells the two apart.
export async function fetchTrainingDefaultsOrSeed(
  profile: string,
  task: string,
): Promise<{ args: TrainingArgs; saved: boolean }> {
  try {
    const got = await request<TrainingDefaultsResponse>(
      `/api/profiles/${encodeURIComponent(profile)}/training-defaults/${encodeURIComponent(task)}`,
    );
    return { args: got.args, saved: true };
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      const seed = await fetchTrainingDefaultsSeed(profile, task);
      return { args: seed.args, saved: false };
    }
    throw err;
  }
}

export function putTrainingDefaults(
  profile: string,
  task: string,
  args: TrainingArgs,
): Promise<TrainingDefaultsResponse> {
  return request<TrainingDefaultsResponse>(
    `/api/profiles/${encodeURIComponent(profile)}/training-defaults/${encodeURIComponent(task)}`,
    { method: "PUT", body: JSON.stringify(args) },
  );
}

export function deleteTrainingDefaults(
  profile: string,
  task: string,
): Promise<void> {
  return request<undefined>(
    `/api/profiles/${encodeURIComponent(profile)}/training-defaults/${encodeURIComponent(task)}`,
    { method: "DELETE" },
  );
}
