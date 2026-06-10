"""Tests for Settings.labeler_export_root property."""

from __future__ import annotations

from pathlib import Path

from pdomain_ocr_trainer_spa.settings import Settings


def test_mode_configured_when_explicit(tmp_path: Path) -> None:
    s = Settings(labeler_export_root=tmp_path)  # type: ignore[arg-type]
    assert s.labeler_export_root == tmp_path


def test_mode_none_when_absent() -> None:
    s = Settings(labeler_export_root=None)
    assert s.labeler_export_root is None
