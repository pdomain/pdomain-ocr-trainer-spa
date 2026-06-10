"""Labeler export root auto-discovery and manifest freshness helpers (Track D).

Isolates all optional pdomain-ops imports so the SPA boots even when
an older pdomain-ops wheel is installed (Track B gating dependency).
See docs/conventions/lint-deviations.md for the approved guarded-import pattern.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path  # noqa: TC003 — used at runtime in method signatures
from typing import Any

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Optional pdomain-ops import — Track B gate
# ---------------------------------------------------------------------------
# This import is intentionally guarded; see docs/conventions/lint-deviations.md
# entry "labeler_export.py: pdomain_ops.suite.shared_paths optional import".
try:
    from pdomain_ops.suite.shared_paths import (  # pyright: ignore[reportMissingImports]
        resolve_shared_path as _resolve_shared_path_impl,
    )

    def _shared_path_lookup(key: str) -> Path | None:
        return _resolve_shared_path_impl(key)

except ImportError:

    def _shared_path_lookup(key: str) -> Path | None:  # type: ignore[misc]
        return None  # pdomain-ops not installed or pre-Track-B version


# ---------------------------------------------------------------------------
# Optional manifest model — falls back to raw JSON dict when import missing
# ---------------------------------------------------------------------------
try:
    from pdomain_ops.schemas.doctr_export import (  # pyright: ignore[reportMissingImports]  # noqa: I001
        DoctrExportManifest,  # pyright: ignore[reportAssignmentType]
        read_manifest as _read_manifest_impl,
    )

    def read_export_manifest(export_root: Path) -> DoctrExportManifest | None:
        """Read the manifest.json from an export root; None if absent or unreadable."""
        if not export_root.exists():
            return None
        return _read_manifest_impl(export_root)  # pyright: ignore[reportReturnType]

except ImportError:

    class DoctrExportManifest(BaseModel):  # type: ignore[no-redef]
        """Fallback manifest model when pdomain-ops pre-Track-B is installed.

        The on-disk JSON key is ``"schema"``; Pydantic reserves that attribute
        name on BaseModel, so we use ``schema_key`` with an alias.
        """

        model_config = {"populate_by_name": True}

        schema_key: str = ""  # on-disk key: "schema"
        version: int = 0
        generated_at: str = ""
        app: str = ""
        projects: dict[str, Any] = {}

        @classmethod
        def model_validate(cls, obj: Any, *args: Any, **kwargs: Any) -> DoctrExportManifest:  # type: ignore[override]
            """Accept both ``"schema"`` and ``"schema_key"`` from on-disk JSON."""
            if isinstance(obj, dict) and "schema" in obj and "schema_key" not in obj:
                obj = {**obj, "schema_key": obj.pop("schema")}
            return super().model_validate(obj, *args, **kwargs)

    def read_export_manifest(export_root: Path) -> DoctrExportManifest | None:  # type: ignore[misc]
        """Read manifest.json from disk using the fallback model."""
        if not export_root.exists():
            return None
        manifest_path = export_root / "manifest.json"
        if not manifest_path.exists():
            return None
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return DoctrExportManifest.model_validate(data)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


class ExportRootMode(str, Enum):
    """How the active labeler export root was resolved."""

    configured = "configured"
    discovered = "discovered"
    absent = "absent"


def resolve_export_root(
    explicit: Path | None,
) -> tuple[Path | None, ExportRootMode]:
    """Return (export_root, mode). Explicit setting always wins over discovery."""
    if explicit is not None:
        return explicit, ExportRootMode.configured
    discovered = _shared_path_lookup("doctr-export-root")
    if discovered is not None:
        return discovered, ExportRootMode.discovered
    return None, ExportRootMode.absent


# ---------------------------------------------------------------------------
# Freshness record — persisted per-profile in app_data_root
# ---------------------------------------------------------------------------


class ExportFreshnessRecord(BaseModel):
    """Persisted record of the last-seen exported_at per project_id.

    Stored as JSON at app_data_root/profiles/<profile>/freshness_state.json,
    alongside the existing kanban_state.json (same directory pattern).
    """

    project_seen_at: dict[str, str] = {}

    def save(self, path: Path) -> None:
        """Write freshness record to disk as JSON (creates parent dirs)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"version": 1, "project_seen_at": self.project_seen_at},
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> ExportFreshnessRecord:
        """Load freshness record from disk; returns empty record if absent or corrupt."""
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        return cls(project_seen_at=data.get("project_seen_at", {}))
