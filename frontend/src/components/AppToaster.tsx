// AppToaster — the single sonner <Toaster> mount (spec 11-notifications §6).
//
// `<Toaster>` is mounted once at the App root.
// `emitToast` lives in `../lib/toastEmitter` so this file only exports
// React components (react-refresh/only-export-components constraint).

import React from "react";
import { Toaster as SonnerToaster } from "sonner";

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
