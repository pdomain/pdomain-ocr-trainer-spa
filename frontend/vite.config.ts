import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // pdomain-ui ships dist files compiled with jsxDEV (dev-mode transform).
      // In production, react/jsx-dev-runtime.production.js exports jsxDEV=undefined,
      // causing "TypeError: jsxDEV is not a function". This alias routes all jsxDEV
      // calls through our shim which re-exports jsxDEV = jsx from jsx-runtime.
      // Remove once pdomain-ui is rebuilt with the production JSX transform.
      "react/jsx-dev-runtime": resolve(__dirname, "src/jsx-dev-runtime-shim.ts"),
    },
  },
  build: {
    outDir: resolve(__dirname, "../src/pdomain_ocr_trainer_spa/static"),
    emptyOutDir: true,
  },
  server: {
    port: 5174,
    proxy: {
      "/api": {
        target: "http://localhost:8081",
        changeOrigin: true,
      },
      "/env.js": {
        target: "http://localhost:8081",
        changeOrigin: true,
      },
    },
  },
});
