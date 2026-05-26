"""AppState — the per-process state bundle (spec 01-data-models §AppState).

Lives at ``app.state.app_state``; routes receive it via ``Depends(get_app_state)``.
M1 establishes the adapter seam; ``profiles`` / ``runs`` stay empty until their
own milestones populate them.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from fastapi import Request  # noqa: TC002 — runtime import: FastAPI resolves get_app_state's annotation

if TYPE_CHECKING:
    from pdomain_ocr_ops.gpu.protocols import LongJobRunner

    from pdomain_ocr_trainer_spa.adapters.auth import IAuth
    from pdomain_ocr_trainer_spa.adapters.dataset_sources import IDatasetSource
    from pdomain_ocr_trainer_spa.adapters.model_registry import IModelRegistry
    from pdomain_ocr_trainer_spa.adapters.storage import IStorage
    from pdomain_ocr_trainer_spa.settings import Settings


@dataclass
class AppState:
    """Adapter bundle + in-memory caches for one FastAPI process."""

    settings: Settings
    storage: IStorage
    auth: IAuth
    dataset_sources: list[IDatasetSource]
    model_registry: IModelRegistry
    job_runner: LongJobRunner

    profiles: dict[str, Any] = field(default_factory=dict)
    runs: dict[str, Any] = field(default_factory=dict)
    notifications: deque[Any] = field(default_factory=lambda: deque(maxlen=200))

    def hydrate_from_disk(self) -> None:
        """Reconcile on-disk state at boot.

        Runs are reconciled per D-T3: any run left ``running`` with no live
        job is marked ``failed``. Imported lazily to keep the import graph of
        ``core`` free of the ``domain`` layer.
        """
        from pdomain_ocr_trainer_spa.domain.runs import hydrate_runs

        hydrate_runs(self)


def get_app_state(request: Request) -> AppState:
    """FastAPI dependency — return the AppState stored on ``app.state``."""
    return request.app.state.app_state
