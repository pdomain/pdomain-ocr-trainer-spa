# Lint deviations

Every `# noqa` / `# pyright: ignore` / `[tool.ruff.lint]` ignore in the
codebase is catalogued here with its justification. See
`CONVENTIONS.md` → "Document every lint-rule suppression".

| Tool | Rule | Location | Justification |
|---|---|---|---|
| ruff | TC003 | `src/pdomain_ocr_trainer_spa/core/models.py` (`datetime` import) | The class is a pydantic field annotation; pydantic resolves annotations at model-build time, so the import must stay at runtime scope. |
| ruff | TC001 | `src/pdomain_ocr_trainer_spa/core/models.py` (`TaskEnum`, `JobState` imports) | Same as above — pydantic field annotation needs the symbol importable at runtime. |
| ruff | TC002 | `src/pdomain_ocr_trainer_spa/core/app_state.py` (`fastapi.Request` import) | `get_app_state` is a FastAPI dependency; FastAPI resolves its `request: Request` annotation at runtime, so the import must stay at runtime scope. |
| basedpyright | reportReturnType | `src/pdomain_ocr_trainer_spa/adapters/builders.py` (`build_job_runner`, both returns) | The pdomain-ops `LongJobRunner` Protocol declares `stream_events` as `async def ... -> AsyncIterator`; every concrete impl (including pdomain-ops' own `LocalLongJobRunner`) implements it as an async generator. basedpyright flags the structural mismatch even for the upstream impl. The ignore tracks an upstream Protocol-shape quirk; revisit when pdomain-ops corrects the Protocol annotation. |
| basedpyright | reportGeneralTypeIssues | `src/pdomain_ocr_trainer_spa/api/jobs.py` (`_event_stream`, `async for`) | Same upstream quirk: because the Protocol types `stream_events` as `async def -> AsyncIterator`, calling it appears to yield a coroutine rather than an async-iterable. Every real impl is an async generator, so `async for` is correct at runtime. Revisit when pdomain-ops corrects the Protocol annotation. |
