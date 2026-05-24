// errorMessages — maps every backend ErrorEnvelope.code to a Toast
// (spec 11-notifications §2.1).
//
// Codes without an explicit entry fall back to a generic error toast
// built from the envelope's own message + code. The coverage smoke test
// (`errorMessages.test.ts`) asserts every code in `api/errors.ts`
// `ERROR_CODES` has an entry here — drift fails CI.

import type { ErrorEnvelope } from "../api/errors";
import { ERROR_CODES } from "../api/errors";
import type { Toast } from "./toast";

/** Builds a Toast from an ErrorEnvelope for one specific error code. */
export type ErrorToastBuilder = (env: ErrorEnvelope) => Toast;

function detailCount(env: ErrorEnvelope): number {
  return env.details?.length ?? 0;
}

/** Per-code toast builders. Keyed by the stable `ErrorEnvelope.code`. */
export const errorMessages: Record<string, ErrorToastBuilder> = {
  // --- dataset kanban -----------------------------------------------------
  "dataset.apply_failed": (env) => ({
    kind: "error",
    title: "Apply failed",
    description:
      env.message ||
      "Some staged moves could not be committed. The board has been " +
        "reset to the server's truth.",
  }),
  "dataset.apply_key_missing": (env) => ({
    kind: "error",
    title: "Stale staged move",
    description: `${detailCount(env)} chip(s) no longer exist on disk. Rescan and try again.`,
  }),
  "dataset.task_unsupported": () => ({
    kind: "error",
    title: "Unsupported task",
    description: "This profile does not support the requested dataset task.",
  }),
  // --- eval ---------------------------------------------------------------
  "eval.not_an_eval": () => ({
    kind: "error",
    title: "Not an eval run",
    description:
      "That run id is a training run, not an eval — no result to show.",
  }),
  "eval.result_missing": () => ({
    kind: "error",
    title: "Eval result missing",
    description:
      "The eval finished but no result file was written. Re-run the eval.",
  }),
  "eval.run_failed": (env) => ({
    kind: "error",
    title: "Eval failed",
    description:
      env.message || "The evaluation run did not finish successfully.",
  }),
  // --- jobs ---------------------------------------------------------------
  "job.unknown": () => ({
    kind: "error",
    title: "Unknown job",
    description: "That job id is not known — it may have been pruned.",
  }),
  // --- models -------------------------------------------------------------
  "model.in_use": () => ({
    kind: "error",
    title: "Model in use",
    description:
      "This model is referenced by an active run and cannot be deleted.",
  }),
  "model.invalid_name": (env) => ({
    kind: "error",
    title: "Invalid model name",
    description:
      env.message ||
      "The model name does not match the pd-{language}-{typeface}-{task} convention.",
  }),
  "model.name_taken": () => ({
    kind: "error",
    title: "Name already taken",
    description:
      "Another model already uses that name. Choose a different one.",
  }),
  "model.unknown": () => ({
    kind: "error",
    title: "Unknown model",
    description:
      "That model is not in the registry — it may have been deleted.",
  }),
  // --- profiles -----------------------------------------------------------
  "profile.bad_typeface": (env) => ({
    kind: "error",
    title: "Invalid typeface",
    description:
      env.message || "The typeface is not one of the supported values.",
  }),
  "profile.exists": () => ({
    kind: "error",
    title: "Profile exists",
    description: "A profile with that name already exists.",
  }),
  "profile.has_data": () => ({
    kind: "error",
    title: "Profile has data",
    description:
      "This profile still has training data. Remove its datasets before deleting it.",
  }),
  "profile.is_base": () => ({
    kind: "error",
    title: "Base profile",
    description: "The base profile cannot be edited or deleted.",
  }),
  "profile.not_found": () => ({
    kind: "error",
    title: "Profile not found",
    description: "That profile no longer exists.",
  }),
  // --- runs ---------------------------------------------------------------
  "run.already_running": () => ({
    kind: "error",
    title: "Run already active",
    description:
      "A run for this profile/task is already running. Wait for it to finish.",
  }),
  "run.has_artefacts": () => ({
    kind: "error",
    title: "Run has artefacts",
    description: "This run produced artefacts on disk and cannot be deleted.",
  }),
  "run.no_training_data": () => ({
    kind: "error",
    title: "No training data",
    description: "This profile has no labelled data for the selected task.",
  }),
  "run.not_terminal": () => ({
    kind: "error",
    title: "Run still active",
    description: "This action is only available once the run has finished.",
  }),
  "run.profile_incomplete": (env) => ({
    kind: "error",
    title: "Profile incomplete",
    description:
      env.message ||
      "The profile is missing a language or typeface needed to mint a model name.",
  }),
  "run.task_unsupported": () => ({
    kind: "error",
    title: "Unsupported task",
    description:
      "The selected training task is not supported for this profile.",
  }),
  "run.unknown": () => ({
    kind: "error",
    title: "Unknown run",
    description: "That run id is not known — it may have been pruned.",
  }),
  // --- training defaults --------------------------------------------------
  "training_defaults.not_set": () => ({
    kind: "error",
    title: "No saved defaults",
    description:
      "This profile has no saved training defaults for that task yet.",
  }),
  "training_defaults.task_unsupported": () => ({
    kind: "error",
    title: "Unsupported task",
    description: "Training defaults are not available for that task.",
  }),
  // --- worker / training failure -----------------------------------------
  "training.cuda_oom": () => ({
    kind: "error",
    title: "Out of GPU memory",
    description:
      "The trainer ran out of CUDA memory. Try cloning the run with a smaller batch size.",
  }),
  // --- publish ------------------------------------------------------------
  "publish.disabled": () => ({
    kind: "error",
    title: "Publishing disabled",
    description:
      "Hugging Face publishing is turned off. Enable it in settings to publish.",
  }),
  "publish.license_missing": (env) => ({
    kind: "error",
    title: "Missing license",
    description: `${detailCount(env)} row(s) have no license. Set a per-row license before publishing.`,
  }),
  // --- deferred adapters --------------------------------------------------
  "adapter.not_implemented": (env) => ({
    kind: "error",
    title: "Not implemented",
    description:
      env.message || "That capability is not available in this build.",
  }),
};

/**
 * Resolve an ErrorEnvelope to a Toast.
 *
 * Uses the per-code builder when one exists, otherwise falls back to a
 * generic error toast carrying the envelope's own message and code
 * (spec 11 §2.1).
 */
export function toastFromError(env: ErrorEnvelope): Toast {
  const builder = errorMessages[env.code];
  if (builder !== undefined) {
    return builder(env);
  }
  return {
    kind: "error",
    title: env.message || "Something went wrong",
    description: env.code,
  };
}

/** All error codes that lack an explicit `errorMessages` entry (for tests). */
export function uncoveredErrorCodes(): string[] {
  return ERROR_CODES.filter((code) => !(code in errorMessages));
}
