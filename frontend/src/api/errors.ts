// Canonical error-code inventory + ErrorEnvelope wire type (spec 02 §7).
//
// Spec 11 §2.1 ultimately keys `errorMessages` off the OpenAPI-generated
// `api/types.ts` string-literal union. That export gate (spec 02 §8) is
// not wired yet, so this module is the hand-maintained source of truth
// until it is. Every code below is raised by an `AppError` in the backend
// (`grep AppError src/pdomain_ocr_trainer_spa`) or named by a spec as a worker
// failure code. The coverage smoke test asserts `errorMessages` covers
// every entry here — drift fails CI.

/** Stable error-code string-literal union (mirror of backend `AppError.code`). */
export const ERROR_CODES = [
  // dataset kanban
  "dataset.apply_failed",
  "dataset.apply_key_missing",
  "dataset.task_unsupported",
  // eval
  "eval.not_an_eval",
  "eval.result_missing",
  "eval.run_failed",
  // jobs
  "job.unknown",
  // models
  "model.in_use",
  "model.invalid_name",
  "model.name_taken",
  "model.unknown",
  // profiles
  "profile.bad_typeface",
  "profile.exists",
  "profile.has_data",
  "profile.is_base",
  "profile.not_found",
  // runs
  "run.already_running",
  "run.has_artefacts",
  "run.no_training_data",
  "run.not_terminal",
  "run.profile_incomplete",
  "run.task_unsupported",
  "run.unknown",
  // training defaults
  "training_defaults.not_set",
  "training_defaults.task_unsupported",
  // worker / training failure codes (spec 06 §, 02 §7)
  "training.cuda_oom",
  // publish (spec 09)
  "publish.disabled",
  "publish.license_missing",
  // deferred adapters
  "adapter.not_implemented",
] as const;

/** A backend error code (stable string). */
export type ErrorCode = (typeof ERROR_CODES)[number];

/** One field-level validation error (spec 02 §7 `FieldError`). */
export interface FieldError {
  loc: string[];
  msg: string;
}

/** The JSON body returned for every non-2xx response (spec 02 §7). */
export interface ErrorEnvelope {
  code: string;
  message: string;
  details?: FieldError[] | null;
  request_id?: string;
}
