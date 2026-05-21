// appEnv — typed, tolerant accessor for the `window.__APP_ENV__` blob
// injected by the backend `/env.js` route (spec 13 §6, spec 15).
//
// `/env.js` is only present when the SPA is served by the FastAPI
// backend; under Vite dev or vitest the blob is absent, so every
// field has a safe fallback. The driver-contract version is the
// stable handshake a future Playwright driver pins against.

/** Shape of `window.__APP_ENV__` as emitted by `api/env_js.py`. */
export interface AppEnv {
  version: string;
  driverContractVersion: number;
  features: Record<string, boolean>;
}

const FALLBACK: AppEnv = {
  version: "dev",
  driverContractVersion: 1,
  features: {},
};

declare global {
  interface Window {
    __APP_ENV__?: Partial<AppEnv>;
  }
}

/** Read `window.__APP_ENV__`, merged over safe fallbacks. */
export function getAppEnv(): AppEnv {
  const raw = typeof window !== "undefined" ? window.__APP_ENV__ : undefined;
  return {
    version: raw?.version ?? FALLBACK.version,
    driverContractVersion:
      raw?.driverContractVersion ?? FALLBACK.driverContractVersion,
    features: raw?.features ?? FALLBACK.features,
  };
}
