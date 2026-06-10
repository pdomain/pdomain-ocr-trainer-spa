/**
 * Shim for react/jsx-dev-runtime → react/jsx-runtime.
 *
 * pdomain-ui ships its dist files compiled with jsxDEV (the React dev-mode transform).
 * In production builds, react/jsx-dev-runtime.production.js leaves jsxDEV undefined,
 * causing "TypeError: jsxDEV is not a function" at runtime.
 *
 * This shim re-exports jsxDEV = jsx so both dev and prod builds work correctly.
 * vite.config.ts aliases "react/jsx-dev-runtime" → this file.
 *
 * Remove this shim once pdomain-ui is rebuilt with the production JSX transform.
 */
export { jsx as jsxDEV, jsxs, Fragment } from "react/jsx-runtime";
