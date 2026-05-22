"""Unit tests for domain/banners.py — banner synthesis (spec 11 §3)."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, NamedTuple

import pytest

from pd_ocr_trainer_spa.domain import banners as dom

if TYPE_CHECKING:
    from pathlib import Path

    from pd_ocr_trainer_spa.settings import Settings


class _Usage(NamedTuple):
    total: int
    used: int
    free: int


def test_no_banners_for_healthy_env(settings: Settings) -> None:
    """Default settings (hf off, ample disk) produce an empty list."""
    assert dom.synthesize_banners(settings) == []


def test_disk_low_banner_fires_below_threshold(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partition under 5% free yields a non-dismissible error banner."""

    def _fake_usage(_path: Path) -> _Usage:
        return _Usage(total=1000, used=970, free=30)  # 3% free

    monkeypatch.setattr(shutil, "disk_usage", _fake_usage)
    result = dom.synthesize_banners(settings)

    assert [b.id for b in result] == ["disk-low"]
    disk = result[0]
    assert disk.severity == "error"
    assert disk.dismissible is False


def test_disk_ok_above_threshold_no_banner(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partition with >= 5% free yields no disk banner."""

    def _fake_usage(_path: Path) -> _Usage:
        return _Usage(total=1000, used=500, free=500)

    monkeypatch.setattr(shutil, "disk_usage", _fake_usage)
    assert dom.synthesize_banners(settings) == []


def test_banner_order_is_deterministic(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """hf-token-missing precedes disk-low when both fire."""
    settings.enable_hf_publish = True
    settings.hf_token_path = settings.app_data_root / "missing"

    def _fake_usage(_path: Path) -> _Usage:
        return _Usage(total=1000, used=999, free=1)

    monkeypatch.setattr(shutil, "disk_usage", _fake_usage)
    assert [b.id for b in dom.synthesize_banners(settings)] == [
        "hf-token-missing",
        "disk-low",
    ]


# ---------------------------------------------------------------------------
# M10 — HF read path: banner fires when token path configured but absent
# ---------------------------------------------------------------------------


def test_hf_token_missing_banner_fires_for_read_path(settings: Settings) -> None:
    """hf-token-missing fires when hf_token_path is set but the file is absent.

    M10 extends the banner to cover the HF read path (datasets.load_dataset)
    in addition to the publish path.  hf_token_path = a Path that doesn't
    exist should always surface the banner — enable_hf_publish is irrelevant.
    """
    settings.enable_hf_publish = False  # read path only
    settings.hf_token_path = settings.app_data_root / "nonexistent-token"

    banners = dom.synthesize_banners(settings)
    assert any(b.id == "hf-token-missing" for b in banners)


def test_hf_no_token_path_configured_no_banner(settings: Settings) -> None:
    """When hf_token_path is None the HF token banner must NOT fire.

    The user has not configured HF at all; we shouldn't nag them.
    """
    settings.enable_hf_publish = False
    settings.hf_token_path = None

    banners = dom.synthesize_banners(settings)
    assert not any(b.id == "hf-token-missing" for b in banners)


def test_hf_token_present_suppresses_banner_for_read_path(
    settings: Settings, tmp_path: Path
) -> None:
    """An existing token file suppresses hf-token-missing even with publish off."""
    token = tmp_path / "token"
    token.write_text("hf_xxx", encoding="utf-8")
    settings.enable_hf_publish = False
    settings.hf_token_path = token

    banners = dom.synthesize_banners(settings)
    assert not any(b.id == "hf-token-missing" for b in banners)
