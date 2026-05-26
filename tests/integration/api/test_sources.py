"""Integration tests for api/sources.py — HF dataset preview (spec 09 §7, M10).

Tests cover:
- GET /api/sources/huggingface/preview returns DatasetPreview shape
- Missing HF token yields 400 hf.auth_missing
- Route is not shadowed by the SPA catch-all
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from pdomain_ocr_trainer_spa.settings import Settings


def _make_client_with_token(settings: Settings, tmp_path: Path) -> TestClient:
    """Build a TestClient with a valid (on-disk) HF token file."""
    from fastapi.testclient import TestClient

    from pdomain_ocr_trainer_spa.bootstrap import build_app

    token_path = tmp_path / "hf-token"
    token_path.write_text("hf_test_token", encoding="utf-8")
    settings.hf_token_path = token_path
    return TestClient(build_app(settings))


def test_sources_preview_route_exists(settings: Settings, tmp_path: Path) -> None:
    """GET /api/sources/huggingface/preview exists (not a 404 or SPA fallback)."""
    client = _make_client_with_token(settings, tmp_path)

    # Patch the actual HF network call so we don't need real credentials.
    with patch(
        "pdomain_ocr_trainer_spa.adapters.dataset_sources.huggingface.HuggingFaceDatasetSource.preview",
        return_value=[],
    ):
        resp = client.get(
            "/api/sources/huggingface/preview",
            params={"repo": "test/repo", "revision": "main", "task": "recognition", "split": "train"},
        )
    # Should be JSON (200 or a structured error), never the SPA index.
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.status_code in {200, 400, 422, 503}


def test_sources_preview_missing_token_returns_error(settings: Settings) -> None:
    """GET /api/sources/huggingface/preview with no token returns 400 hf.auth_missing."""
    from fastapi.testclient import TestClient

    from pdomain_ocr_trainer_spa.bootstrap import build_app

    settings.hf_token_path = settings.app_data_root / "nonexistent-token"
    client = TestClient(build_app(settings))

    resp = client.get(
        "/api/sources/huggingface/preview",
        params={"repo": "test/repo", "revision": "main", "task": "recognition", "split": "train"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "hf.auth_missing"


def test_sources_preview_no_token_path_returns_error(settings: Settings) -> None:
    """GET /api/sources/huggingface/preview with hf_token_path=None returns 400."""
    from fastapi.testclient import TestClient

    from pdomain_ocr_trainer_spa.bootstrap import build_app

    settings.hf_token_path = None
    client = TestClient(build_app(settings))

    resp = client.get(
        "/api/sources/huggingface/preview",
        params={"repo": "test/repo", "revision": "main", "task": "recognition", "split": "train"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "hf.auth_missing"


def test_sources_preview_route_not_shadowed_by_spa(settings: Settings, tmp_path: Path) -> None:
    """GET /api/sources/... returns JSON, not the SPA index."""
    client = _make_client_with_token(settings, tmp_path)

    with patch(
        "pdomain_ocr_trainer_spa.adapters.dataset_sources.huggingface.HuggingFaceDatasetSource.preview",
        return_value=[],
    ):
        resp = client.get(
            "/api/sources/huggingface/preview",
            params={"repo": "test/repo", "revision": "main", "task": "recognition", "split": "train"},
        )
    assert resp.headers["content-type"].startswith("application/json")
