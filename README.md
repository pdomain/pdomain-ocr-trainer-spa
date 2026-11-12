---
Status: active
Owner: CT
Created: 2026-05-21
Last verified: 2026-11-12
Kind: architecture
---

# pdomain-ocr-trainer-spa

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Read when:** orienting to the product, its shipped scope, or current work.
- **Search terms:** OCR trainer, FastAPI, React, workflows, architecture.

This repository contains the FastAPI and React/TypeScript OCR trainer SPA. It
replaces the NiceGUI user interface from
[pdomain-ocr-training](https://github.com/pdomain/pdomain-ocr-training) while
continuing to use that package's training contracts.

The shipped application manages profiles, dataset kanbans, detection and
recognition runs, the model registry, and Hugging Face dataset preview.
Production typeface training, production evaluation, and the publish worker
are not wired. Glyph-classifier training is not implemented. Open work is
[docs/roadmap.md](docs/roadmap.md).

## Current documentation

- [Trainer workflows](docs/architecture/trainer-workflows.md) is the short map.
  Topic pages next to it cover profiles and models, runs and evaluation, the
  shell and jobs, Hugging Face, and labeler import.
- Numbered files under `specs/` are superseded stubs, except
  [specs/13-driver-contract.md](specs/13-driver-contract.md), which the driver
  conformance test still parses. They are not the source of truth.
- [Current state](docs/context/current-state.md),
  [intent map](docs/context/intent-map.md), and
  [decisions](docs/context/decisions.md) separate present truth, remaining work,
  and durable rationale.
- [Development guide](DEVELOPMENT.md) gives repository-backed commands.

## License

The project uses the Unlicense, as declared in `pyproject.toml`.
