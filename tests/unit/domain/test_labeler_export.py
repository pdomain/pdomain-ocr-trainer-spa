"""Tests for labeler export auto-discovery and manifest helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from pdomain_ocr_trainer_spa.domain.labeler_export import (
    ExportFreshnessRecord,
    ExportRootMode,
    read_export_manifest,
    resolve_export_root,
)


def test_explicit_setting_wins(tmp_path: Path) -> None:
    explicit = tmp_path / "explicit-export"
    explicit.mkdir()
    root, mode = resolve_export_root(explicit)
    assert root == explicit
    assert mode == ExportRootMode.configured


def test_auto_discovery_when_setting_absent(tmp_path: Path) -> None:
    discovered = tmp_path / "discovered-export"
    discovered.mkdir()
    with patch(
        "pdomain_ocr_trainer_spa.domain.labeler_export._shared_path_lookup",
        return_value=discovered,
    ):
        root, mode = resolve_export_root(None)
    assert root == discovered
    assert mode == ExportRootMode.discovered


def test_absent_when_both_missing() -> None:
    with patch(
        "pdomain_ocr_trainer_spa.domain.labeler_export._shared_path_lookup",
        return_value=None,
    ):
        root, mode = resolve_export_root(None)
    assert root is None
    assert mode == ExportRootMode.absent


def test_read_manifest_returns_none_when_absent(tmp_path: Path) -> None:
    result = read_export_manifest(tmp_path / "nonexistent")
    assert result is None


def test_read_manifest_returns_manifest(tmp_path: Path) -> None:
    manifest_data = {
        "schema": "pdomain.doctr-export-manifest",
        "version": 1,
        "generated_at": "2026-06-10T12:00:00Z",
        "app": "pdomain-ocr-labeler-spa",
        "projects": {
            "myproj": {
                "exported_at": "2026-06-10T11:00:00Z",
                "page_count": 42,
                "tasks": {"recognition": {"item_count": 42}},
            }
        },
    }
    (tmp_path / "manifest.json").write_text(
        json.dumps(manifest_data),
        encoding="utf-8",
    )
    result = read_export_manifest(tmp_path)
    assert result is not None
    assert "myproj" in result.projects


def test_freshness_record_roundtrip(tmp_path: Path) -> None:
    rec = ExportFreshnessRecord(project_seen_at={"myproj": "2026-06-10T11:00:00Z"})
    path = tmp_path / "freshness_state.json"
    rec.save(path)
    loaded = ExportFreshnessRecord.load(path)
    assert loaded.project_seen_at == {"myproj": "2026-06-10T11:00:00Z"}


def test_freshness_record_load_missing_returns_empty(tmp_path: Path) -> None:
    rec = ExportFreshnessRecord.load(tmp_path / "nonexistent.json")
    assert rec.project_seen_at == {}
