// toastEmitter — maps our Toast contract onto the sonner API.
//
// Extracted from AppToaster.tsx so that the component file only exports
// React components (react-refresh/only-export-components constraint).
//
// `emitToast` is the public entry point used by every call-site that
// wants to emit a toast programmatically (spec 11-notifications §2, §6).

import { toast as sonnerToast } from "sonner";
import type { Toast } from "./toast";
import { toastDuration } from "./toast";

/**
 * Emit a toast through sonner.
 *
 * Returns the sonner-generated id (re-exported per the driver contract's
 * `toast-{id}` testid). A `durationMs` of 0 makes the toast persistent.
 */
export function emitToast(toast: Toast): string | number {
  const duration = toastDuration(toast);
  const options = {
    description: toast.description,
    duration: duration === 0 ? Infinity : duration,
    action: toast.action
      ? { label: toast.action.label, onClick: toast.action.onClick }
      : undefined,
    id: toast.id,
  };
  switch (toast.kind) {
    case "success":
      return sonnerToast.success(toast.title, options);
    case "error":
      return sonnerToast.error(toast.title, options);
    case "warn":
      return sonnerToast.warning(toast.title, options);
    default:
      return sonnerToast.info(toast.title, options);
  }
}
