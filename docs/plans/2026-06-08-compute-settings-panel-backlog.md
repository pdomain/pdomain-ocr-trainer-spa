---
status: backlog
priority: later
repo: pdomain/pdomain-ocr-trainer-spa
---

# Compute Settings Panel Backlog

`pdomain-ocr-trainer-spa` is a GPU-relevant candidate for the shared pdomain ops
Compute settings panel, but it is not ready for this change until the frontend
adopts the shared settings/AppShell surface used by the newer pdomain apps.

## Scope When Revived

- Add the shared pdomain-ui settings surface if it is not already present.
- Expose a Compute settings entry backed by `createApiDeviceConfig()` and
  `useDeviceInfo()`.
- Start a background `GET /api/suite/device` warmup task at SPA startup when the
  Compute panel is exposed.
- Render in-app CUDA setup guidance appropriate for OCR training environments.

## Acceptance

- Training users can see whether CUDA is usable before launching a run.
- Settings shows CPU, usable CUDA devices, and detected but unusable NVIDIA
  hardware.
- Startup performs the compute-state warmup only when the Compute panel is
  exposed.
- CUDA guidance is available inside the app and links to the PyTorch selector.
