# pdomain-ocr-trainer-spa

FastAPI + React/Vite/TS replacement for the NiceGUI-based
[`pdomain-ocr-training`](../pdomain-ocr-training/) UI. Same training and dataset
machinery, web SPA front-end, structurally modelled on
[`pdomain-ocr-labeler-spa`](../pdomain-ocr-labeler-spa/) and
[`pdomain-prep-for-pgdp`](../pdomain-prep-for-pgdp/).

> **Status:** M0–M9 shipped. M10 (HF read path) in progress.
> Implementation is milestone-driven (see
> [`specs/16-milestones.md`](specs/16-milestones.md)).

## What it is

The trainer side of the OCR pipeline: profile management, dataset
kanban (Unassigned / Training / Validation), DocTR detection and recognition
training runs, evaluation slicing, model registry, and Hugging Face dataset /
model publishing. The typeface-classifier dataset and UI workflow ship, but a
real `train_typeface` runner is still unavailable. Glyph-classifier datasets
are reserved, and their training workflow is not implemented yet.

The legacy `pdomain-ocr-training` keeps working unchanged until parity ships
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

Same as the other `pdomain` repos. See `LICENSE` once it lands.
