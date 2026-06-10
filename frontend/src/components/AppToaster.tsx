// AppToaster — the single sonner <Toaster> mount + a typed `emitToast`
// adapter (spec 11-notifications §2, §6).
//
// `<Toaster>` is mounted once at the App root. `emitToast` maps our
// `Toast` contract onto sonner's API, picking the right sonner method
// per `kind` so info/success get `role="status"` and warn/error get
// `role="alert"` (spec 11 §7 — sonner's default behaviour).

import React from "react";
import { Toaster as SonnerToaster, toast as sonnerToast } from "sonner";
import type { Toast } from "../lib/toast";
import { toastDuration } from "../lib/toast";

/** The single sonner toaster mount (spec 11 §6). */
export function AppToaster(): React.JSX.Element {
  return (
    <SonnerToaster
      position="top-right"
      duration={5000}
      closeButton
      expand={false}
      richColors
      theme="system"
    />
  );
}

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
