# Lint deviations

Every `# noqa` / `# pyright: ignore` / `[tool.ruff.lint]` ignore in the
codebase is catalogued here with its justification. See
`CONVENTIONS.md` → "Document every lint-rule suppression".

| Tool | Rule | Location | Justification |
|---|---|---|---|
| ruff | TC003 | `src/pd_ocr_trainer_spa/core/models.py` (`datetime` import) | The class is a pydantic field annotation; pydantic resolves annotations at model-build time, so the import must stay at runtime scope. |
| ruff | TC001 | `src/pd_ocr_trainer_spa/core/models.py` (`TaskEnum` import) | Same as above — pydantic field annotation needs the symbol importable at runtime. |
| basedpyright | reportReturnType | `src/pd_ocr_trainer_spa/adapters/builders.py` (`build_job_runner`, both returns) | The pd-ocr-ops `LongJobRunner` Protocol declares `stream_events` as `async def ... -> AsyncIterator`; every concrete impl (including pd-ocr-ops' own `LocalLongJobRunner`) implements it as an async generator. basedpyright flags the structural mismatch even for the upstream impl. The ignore tracks an upstream Protocol-shape quirk; revisit when pd-ocr-ops corrects the Protocol annotation. |
