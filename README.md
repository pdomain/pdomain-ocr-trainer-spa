# pd-ocr-trainer-spa

FastAPI + React/Vite/TS replacement for the NiceGUI-based
[`pd-ocr-trainer`](../pd-ocr-trainer/) UI. Same training and dataset
machinery, web SPA front-end, structurally modelled on
[`pd-ocr-labeler-spa`](../pd-ocr-labeler-spa/) and
[`pd-prep-for-pgdp`](../pd-prep-for-pgdp/).

> **Status:** spec-only. Implementation is milestone-driven (see
> [`specs/16-milestones.md`](specs/16-milestones.md)).

## What it is

The trainer side of the OCR pipeline: profile management, dataset
kanban (Unassigned / Training / Validation), DocTR detection +
recognition + typeface-classifier + glyph-classifier training runs,
evaluation slicing, model registry, and Hugging Face dataset / model
publishing.

The legacy `pd-ocr-trainer` keeps working unchanged until parity ships
here. Both consume and emit the same on-disk shapes
(`ml-training/<profile>/{detection,recognition}/`,
`ml-validation/<profile>/...`, `matched-ocr/`, the `dist/` model
artefacts) so they can coexist on the same machine during the
transition.

## Specs are the source of truth

Read [`specs/00-overview.md`](specs/00-overview.md) first. Every other
spec is linked from there.

If reality forces a deviation from a spec, **update the spec first,
then the code.** Code that disagrees with the spec is wrong.

Open questions live in [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md).

## License

Same as the other `pd-*` repos. See `LICENSE` once it lands.
