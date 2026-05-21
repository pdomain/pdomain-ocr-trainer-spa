// Toast contract (spec 11-notifications §2).

/** A toast's severity class. */
export type ToastKind = "info" | "success" | "warn" | "error";

/** A client-side navigation action attached to a toast. */
export interface ToastAction {
  label: string;
  onClick: () => void;
}

/** A toast notification (spec 11 §2). */
export interface Toast {
  /** sonner-generated unless overridden. */
  id?: string;
  kind: ToastKind;
  /** Under 50 chars — the long form lives in `description`. */
  title: string;
  description?: string;
  /** Action buttons trigger client-side navigation only. */
  action?: ToastAction;
  /** 0 = persistent; omitted = per-kind default. */
  durationMs?: number;
}

/** Per-kind default auto-dismiss durations in ms (0 = persistent). */
export const TOAST_DURATIONS: Record<ToastKind, number> = {
  info: 5000,
  success: 10000,
  warn: 0,
  error: 0,
};

/** Resolve a toast's effective duration, applying the per-kind default. */
export function toastDuration(toast: Toast): number {
  return toast.durationMs ?? TOAST_DURATIONS[toast.kind];
}
