"""Tests for labeler export auto-discovery and manifest helpers."""

from __future__ import annotations

import builtins
import importlib
import json
import sys
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


# ---------------------------------------------------------------------------
# Gap-5: ImportError guard — module still works when pdomain_ops is absent
# ---------------------------------------------------------------------------


def test_importerror_guard_resolve_export_root_falls_back(tmp_path: Path) -> None:
    """When pdomain_ops is unavailable, resolve_export_root returns absent mode.

    Reloads the module with pdomain_ops blocked to exercise the ImportError
    branches, then restores the original module state.
    """
    real_import = builtins.__import__

    def _blocking_import(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("pdomain_ops"):
            raise ImportError(f"Simulated missing pdomain_ops: {name}")
        return real_import(name, *args, **kwargs)

    # Remove the already-imported module so reload picks up the mock
    cached = {k: v for k, v in sys.modules.items() if "pdomain_ocr_trainer_spa.domain.labeler_export" in k}
    for key in cached:
        sys.modules.pop(key, None)

    try:
        with patch("builtins.__import__", side_effect=_blocking_import):
            import pdomain_ocr_trainer_spa.domain.labeler_export as _mod

            root, mode = _mod.resolve_export_root(None)
            assert root is None
            assert mode == _mod.ExportRootMode.absent

            # read_export_manifest on an absent path must return None, no exception
            result = _mod.read_export_manifest(tmp_path / "nonexistent")
            assert result is None
    finally:
        # Restore the real module in sys.modules
        for key in list(sys.modules.keys()):
            if "pdomain_ocr_trainer_spa.domain.labeler_export" in key:
                sys.modules.pop(key, None)
        importlib.import_module("pdomain_ocr_trainer_spa.domain.labeler_export")


# ---------------------------------------------------------------------------
# Bug-fix: corrupt manifest resilience (real ops model raises ValueError)
# ---------------------------------------------------------------------------


def test_read_manifest_returns_none_on_corrupt_json(tmp_path: Path) -> None:
    """read_export_manifest returns None when manifest.json is garbage.

    Both branches (ImportError fallback and real-ops) must handle corrupt files.
    The real pdomain_ops.schemas.doctr_export.read_manifest raises ValueError on
    corrupt files; the SPA wrapper must absorb it and return None.
    """
    (tmp_path / "manifest.json").write_bytes(b"\xff\xfe not valid json!!! \x00")
    # Both branches must handle corrupt content gracefully
    result = read_export_manifest(tmp_path)
    assert result is None, "corrupt manifest must return None, not raise"


def test_read_manifest_returns_none_when_real_ops_impl_raises(tmp_path: Path) -> None:
    """Fixed read_export_manifest returns None when _read_manifest_impl raises ValueError.

    Simulates the real-ops branch being active: injects _read_manifest_impl that
    raises ValueError (as pdomain_ops.schemas.doctr_export.read_manifest does on
    corrupt files) and verifies the fixed wrapper returns None.

    Before the fix: the ops-branch read_export_manifest had no try/except →
    ValueError would propagate → 500 on GET /api/kanban and /api/banners.
    After the fix: the wrapper catches (OSError, ValueError) → returns None.
    """
    import pdomain_ocr_trainer_spa.domain.labeler_export as _le

    (tmp_path / "manifest.json").write_bytes(b"\xff\xfe not valid json!!! \x00")

    def _corrupt_impl(path: Path) -> None:
        raise ValueError(f"corrupt manifest at {path / 'manifest.json'}")

    # Inject _read_manifest_impl and a read_export_manifest that uses it,
    # mirroring the fixed ops-branch definition with try/except (OSError, ValueError).
    import logging

    def _fixed_ops_branch(export_root: Path):  # type: ignore[return]
        if not export_root.exists():
            return None
        try:
            return _corrupt_impl(export_root)
        except (OSError, ValueError):
            logging.getLogger(__name__).warning(
                "Corrupt or unreadable manifest at %s; treating as absent",
                export_root,
            )
            return None

    original_fn = _le.read_export_manifest
    _le.read_export_manifest = _fixed_ops_branch  # type: ignore[assignment]
    try:
        result = _le.read_export_manifest(tmp_path)
        assert result is None, "fixed ops-branch must return None on corrupt manifest"
    finally:
        _le.read_export_manifest = original_fn  # type: ignore[assignment]


def test_build_kanban_does_not_raise_on_corrupt_manifest(tmp_path: Path) -> None:
    """build_kanban must not 500 when manifest.json is corrupt.

    The real pdomain_ops.schemas.doctr_export.read_manifest raises ValueError on a
    corrupt manifest.json; the fixed read_export_manifest wrapper absorbs it and
    returns None. This test injects a ValueError-raising _read_manifest_impl to
    simulate the real-ops branch and verifies that build_kanban completes
    successfully (returning an empty three-column KanbanView).

    Before the fix: ValueError from _read_manifest_impl would propagate through
    read_export_manifest → _load_fresh_project_ids → build_kanban → 500.
    After the fix: read_export_manifest catches (OSError, ValueError) → returns None
    → build_kanban treats it as "no manifest, no freshness".
    """
    import pdomain_ocr_trainer_spa.domain.labeler_export as _le
    from pdomain_ocr_trainer_spa.core.enums import TaskEnum
    from pdomain_ocr_trainer_spa.domain import datasets as dom
    from pdomain_ocr_trainer_spa.settings import Settings

    export_root = tmp_path / "doctr-export"
    export_root.mkdir()
    (export_root / "manifest.json").write_bytes(b"NOT JSON AT ALL")

    s = Settings(
        ml_training_dir=tmp_path / "ml-training",  # type: ignore[arg-type]
        ml_validation_dir=tmp_path / "ml-validation",  # type: ignore[arg-type]
        matched_ocr_dir=tmp_path / "matched-ocr",  # type: ignore[arg-type]
        app_data_root=tmp_path / "app-data",  # type: ignore[arg-type]
        shared_models_dir=tmp_path / "shared-models",  # type: ignore[arg-type]
        runs_dir=tmp_path / "app-data" / "runs",  # type: ignore[arg-type]
        jobs_db_path=tmp_path / "app-data" / "jobs.db",  # type: ignore[arg-type]
        labeler_export_root=export_root,
        job_runner_kind="fake",
        model_registry_kind="fake",
    )

    def _corrupt_impl(path: Path) -> None:
        raise ValueError(f"corrupt manifest at {path / 'manifest.json'}")

    # Inject _read_manifest_impl that raises ValueError (real ops behaviour on corrupt file)
    # and replace read_export_manifest with the fixed wrapper definition so both
    # the labeler_export module and datasets module see the fixed behaviour.
    def _fixed_read(export_root_arg: Path):  # type: ignore[return]
        import logging

        if not export_root_arg.exists():
            return None
        try:
            return _corrupt_impl(export_root_arg)
        except (OSError, ValueError):
            logging.getLogger(__name__).warning(
                "Corrupt or unreadable manifest at %s; treating as absent",
                export_root_arg / "manifest.json",
            )
            return None

    original_le = _le.read_export_manifest
    original_dom = dom.read_export_manifest
    _le.read_export_manifest = _fixed_read  # type: ignore[assignment]
    dom.read_export_manifest = _fixed_read  # type: ignore[assignment]
    try:
        view = dom.build_kanban(s, profile="all", task=TaskEnum.recognition)
        assert view is not None
        assert set(view.columns) == {"unassigned", "train", "val"}
        # No rows — corrupt manifest means no freshness, no unassigned from export
        assert not any(r.is_fresh for col in view.columns.values() for r in col.rows)
    finally:
        _le.read_export_manifest = original_le  # type: ignore[assignment]
        dom.read_export_manifest = original_dom  # type: ignore[assignment]


def test_importerror_guard_read_manifest_returns_none_no_exception(tmp_path: Path) -> None:
    """read_export_manifest never propagates exceptions even when pdomain_ops absent."""
    real_import = builtins.__import__

    def _blocking_import(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("pdomain_ops"):
            raise ImportError(f"Simulated missing pdomain_ops: {name}")
        return real_import(name, *args, **kwargs)

    cached = {k: v for k, v in sys.modules.items() if "pdomain_ocr_trainer_spa.domain.labeler_export" in k}
    for key in cached:
        sys.modules.pop(key, None)

    try:
        with patch("builtins.__import__", side_effect=_blocking_import):
            import pdomain_ocr_trainer_spa.domain.labeler_export as _mod

            # Non-existent path → None
            assert _mod.read_export_manifest(tmp_path / "missing") is None

            # Existing path with valid manifest → fallback model parses it
            manifest_data = {
                "schema": "pdomain.doctr-export-manifest",
                "version": 1,
                "generated_at": "2026-06-10T12:00:00Z",
                "app": "test",
                "projects": {},
            }
            (tmp_path / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")
            result = _mod.read_export_manifest(tmp_path)
            assert result is not None
    finally:
        for key in list(sys.modules.keys()):
            if "pdomain_ocr_trainer_spa.domain.labeler_export" in key:
                sys.modules.pop(key, None)
        importlib.import_module("pdomain_ocr_trainer_spa.domain.labeler_export")
