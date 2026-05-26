"""Integration tests for api/banners.py — environment banners (spec 11 §3)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from pdomain_ocr_trainer_spa.bootstrap import build_app

if TYPE_CHECKING:
    from pdomain_ocr_trainer_spa.settings import Settings


def test_banners_empty_when_hf_disabled_and_disk_ok(client: TestClient) -> None:
    """The default test settings (hf publish off, tmp disk) yield no banners."""
    resp = client.get("/api/banners")
    assert resp.status_code == 200
    assert resp.json() == {"banners": []}


def test_hf_token_missing_banner_when_enabled_without_token(
    settings: Settings,
) -> None:
    """enable_hf_publish with a missing token file surfaces the warn banner."""
    settings.enable_hf_publish = True
    settings.hf_token_path = settings.app_data_root / "nonexistent-token"
    client = TestClient(build_app(settings))

    banners = client.get("/api/banners").json()["banners"]

    ids = {b["id"] for b in banners}
    assert "hf-token-missing" in ids
    hf = next(b for b in banners if b["id"] == "hf-token-missing")
    assert hf["severity"] == "warn"
    assert hf["dismissible"] is True
    assert hf["action"]["href"] == "/settings"


def test_hf_token_present_suppresses_banner(settings: Settings) -> None:
    """An existing token file means no hf-token-missing banner."""
    token = settings.app_data_root / "token"
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text("hf_xxx", encoding="utf-8")
    settings.enable_hf_publish = True
    settings.hf_token_path = token
    client = TestClient(build_app(settings))

    ids = {b["id"] for b in client.get("/api/banners").json()["banners"]}
    assert "hf-token-missing" not in ids


def test_hf_token_missing_fires_even_when_publish_disabled(settings: Settings) -> None:
    """hf-token-missing fires whenever hf_token_path is set but missing.

    M10: the banner covers the HF read path too, not just publishing.
    enable_hf_publish no longer gates it — the token is required for fetch.
    """
    settings.enable_hf_publish = False
    settings.hf_token_path = settings.app_data_root / "nonexistent-token"
    client = TestClient(build_app(settings))

    ids = {b["id"] for b in client.get("/api/banners").json()["banners"]}
    assert "hf-token-missing" in ids


def test_hf_token_path_none_suppresses_banner(settings: Settings) -> None:
    """When hf_token_path is None (HF not configured), no banner fires."""
    settings.enable_hf_publish = False
    settings.hf_token_path = None
    client = TestClient(build_app(settings))

    ids = {b["id"] for b in client.get("/api/banners").json()["banners"]}
    assert "hf-token-missing" not in ids


def test_banner_route_not_shadowed_by_spa_catchall(client: TestClient) -> None:
    """GET /api/banners is JSON, not the SPA index fallback."""
    resp = client.get("/api/banners")
    assert resp.headers["content-type"].startswith("application/json")
