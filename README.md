---
Status: active
Owner: CT
Created: 2026-05-21
Last verified: 2026-07-14
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
recognition runs, evaluation, models, and Hugging Face read and publish flows.
The typeface dataset and browser workflow are present, but production typeface
training and evaluation still depend on upstream contracts. Glyph-classifier
training is not implemented.

## Current documentation

- [Trainer workflows](docs/architecture/trainer-workflows.md) records shipped
  architecture and evidence.
- [Labeler import and freshness](docs/architecture/labeler-import-and-freshness.md)
  records the labeler export boundary.
- [Current state](docs/context/current-state.md),
  [intent map](docs/context/intent-map.md), and
  [decisions](docs/context/decisions.md) separate present truth, remaining work,
  and durable rationale.
- [Development guide](DEVELOPMENT.md) gives repository-backed commands.

## License

The project uses the Unlicense, as declared in `pyproject.toml`.
