"""api/datasets.py — dataset-kanban REST surface (spec 02 §6.3, spec 05).

Kanban reassignment is staged client-side and committed atomically by
``apply`` (D-T23). M4 implements the **recognition** task only.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Response

from pdomain_ocr_trainer_spa.core.app_state import get_app_state
from pdomain_ocr_trainer_spa.core.enums import TaskEnum  # noqa: TC001 — pydantic resolves at model-build time
from pdomain_ocr_trainer_spa.core.models import (  # noqa: TC001 — pydantic resolves these at model-build time
    ApplyAssignmentRequest,
    IncludeTogglesRequest,
    KanbanView,
)
from pdomain_ocr_trainer_spa.domain import datasets as dom

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.core.app_state import AppState

router = APIRouter(prefix="/api/profiles", tags=["datasets"])


@router.get("/{profile}/datasets/{task}/kanban")
async def get_kanban(
    profile: str,
    task: TaskEnum,
    state: AppState = Depends(get_app_state),
) -> KanbanView:
    """Return the committed kanban view for a ``(profile, task)`` pair (spec 05 §3)."""
    return dom.build_kanban(state.settings, profile=profile, task=task)


@router.post("/{profile}/datasets/{task}/scan")
async def scan_kanban(
    profile: str,
    task: TaskEnum,
    state: AppState = Depends(get_app_state),
) -> KanbanView:
    """Force a re-walk of the export root + on-disk dirs (spec 05 §3).

    The kanban is computed fresh from disk on every call, so ``scan`` and
    ``kanban`` are equivalent server-side — the distinction is a client signal.
    """
    return dom.build_kanban(state.settings, profile=profile, task=task)


@router.post("/{profile}/datasets/{task}/include-toggles")
async def set_include_toggles(
    profile: str,
    task: TaskEnum,
    body: IncludeTogglesRequest,
    state: AppState = Depends(get_app_state),
) -> KanbanView:
    """Persist the include-toggles and return the refreshed view (spec 05 §5)."""
    dom.set_include_toggles(
        state.settings,
        profile=profile,
        include_detection=body.include_detection,
        include_recognition=body.include_recognition,
    )
    return dom.build_kanban(state.settings, profile=profile, task=task)


@router.post("/{profile}/datasets/{task}/apply")
async def apply_assignments(
    profile: str,
    task: TaskEnum,
    body: ApplyAssignmentRequest,
    response: Response,
    state: AppState = Depends(get_app_state),
) -> KanbanView:
    """Commit the full staged target-split assignment to disk (spec 05 §4).

    Partial failures surface in the ``X-Apply-Errors`` response header; a
    fully-failed apply raises ``409 dataset.apply_failed``.
    """
    view, errors = dom.apply_assignments(
        state.settings,
        profile=profile,
        task=task,
        request=body,
        raise_on_total_failure=True,
    )
    if errors:
        response.headers["X-Apply-Errors"] = json.dumps(errors)
    return view
