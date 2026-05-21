"""AppState — the per-process state bundle (spec 01-data-models §AppState).

Lives at ``app.state.app_state``; routes receive it via ``Depends(get_app_state)``.
M1 establishes the adapter seam; ``profiles`` / ``runs`` stay empty until their
own milestones populate them.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import Request
    from pd_ocr_ops.gpu.protocols import LongJobRunner

    from pd_ocr_trainer_spa.adapters.auth import IAuth
    from pd_ocr_trainer_spa.adapters.dataset_sources import IDatasetSource
    from pd_ocr_trainer_spa.adapters.model_registry import IModelRegistry
    from pd_ocr_trainer_spa.adapters.storage import IStorage
    from pd_ocr_trainer_spa.settings import Settings


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

        M1 has no profiles or runs on disk, so this is a no-op placeholder;
        run reconciliation (D-T3) lands with the runs milestone.
        """


def get_app_state(request: Request) -> AppState:
    """FastAPI dependency — return the AppState stored on ``app.state``."""
    return request.app.state.app_state
