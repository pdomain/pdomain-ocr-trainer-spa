"""GET /api/ui-prefs + PATCH /api/ui-prefs — UIPrefs persistence for AppShell."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()

_FILENAME = "ui_prefs.json"


def _prefs_path(request: Request) -> Path:
    settings = getattr(request.app.state, "settings", None)
    if settings is not None:
        return Path(settings.app_data_root) / _FILENAME
    # Fallback for tests that don't pass settings
    return Path.home() / ".local" / "share" / "pdomain-ocr-trainer-spa" / _FILENAME


class UIPrefs(BaseModel):
    """User interface preferences persisted for AppShell."""

    theme: str = "dark"
    density: str = "normal"
    fontScale: float = 1.0  # noqa: N815  # camelCase matches frontend contract


def _load(path: Path) -> UIPrefs:
    if not path.exists():
        return UIPrefs()
    try:
        return UIPrefs(**json.loads(path.read_text()))
    except Exception:  # noqa: BLE001  # corrupt file → return defaults
        return UIPrefs()


def _save(path: Path, prefs: UIPrefs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prefs.model_dump_json())


@router.get("/api/ui-prefs", response_model=UIPrefs)
async def get_ui_prefs(request: Request) -> UIPrefs:
    """Return current UIPrefs (defaults if not yet persisted)."""
    return _load(_prefs_path(request))


@router.patch("/api/ui-prefs", response_model=UIPrefs)
async def patch_ui_prefs(request: Request, partial: dict[str, Any]) -> UIPrefs:
    """Partially update UIPrefs and persist."""
    path = _prefs_path(request)
    current = _load(path)
    updated = current.model_copy(update={k: v for k, v in partial.items() if v is not None})
    _save(path, updated)
    return updated
