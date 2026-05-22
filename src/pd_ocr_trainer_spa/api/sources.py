"""api/sources.py — HF dataset-source preview endpoint (spec 09 §7, M10).

Routes:
    GET /api/sources/huggingface/preview
        Query: repo, revision, task, split
        Returns: DatasetPreview (first ≤50 rows)

Authentication: reads Settings.hf_token_path — missing → 400 hf.auth_missing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from pd_ocr_trainer_spa.core.app_state import get_app_state
from pd_ocr_trainer_spa.core.errors import AppError

if TYPE_CHECKING:
    from pd_ocr_trainer_spa.core.app_state import AppState
    from pd_ocr_trainer_spa.settings import Settings

router = APIRouter(prefix="/api/sources", tags=["sources"])

_PREVIEW_CACHE_SECONDS = 300  # 5 min per spec 09 §7

SplitLiteral = Literal["train", "val", "test"]


class DatasetPreview(BaseModel):
    """First ≤50 rows of an HF dataset (spec 09 §7)."""

    repo: str
    revision: str
    task: str
    rows: list[dict[str, Any]] = []
    total: int = 0


def _require_hf_token(settings: Settings) -> str:
    """Read the HF token from disk — raises 400 hf.auth_missing if absent."""
    token_path = settings.hf_token_path
    if token_path is None or not token_path.exists():
        path_hint = str(token_path) if token_path is not None else "not configured"
        raise AppError(
            code="hf.auth_missing",
            message=(
                f"HF token not found ({path_hint}). "
                "Set PD_OCR_TRAINER_SPA_HF_TOKEN_PATH to a readable token file."
            ),
            status_code=400,
        )
    return token_path.read_text(encoding="utf-8").strip()


@router.get("/huggingface/preview", response_model=DatasetPreview)
async def preview_hf_dataset(
    repo: str = Query(..., description="HF repo id, e.g. 'owner/repo-name'"),
    revision: str = Query("main", description="Git ref (branch, tag, or commit)"),
    task: str = Query(..., description="Task type: recognition | detection | …"),
    split: SplitLiteral = Query("train", description="Dataset split"),
    state: AppState = Depends(get_app_state),
) -> DatasetPreview:
    """Return the first ≤50 rows of an HF dataset for preview (spec 09 §7).

    Checks HF token first — returns ``400 hf.auth_missing`` when absent.
    The heavy HuggingFace I/O (``datasets.load_dataset``) is delegated to
    the adapter so the route stays thin and testable.
    """
    token = _require_hf_token(state.settings)  # raises 400 if missing

    from pd_ocr_trainer_spa.adapters.dataset_sources.huggingface import (
        HuggingFaceDatasetSource,
    )

    source = HuggingFaceDatasetSource(state.settings, token=token)
    rows = source.preview(repo=repo, revision=revision, task=task, split=split)
    return DatasetPreview(
        repo=repo,
        revision=revision,
        task=task,
        rows=rows[:50],
        total=len(rows),
    )
