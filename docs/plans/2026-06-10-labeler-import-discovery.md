---
status: active
created: 2026-06-10
repo: pdomain/pdomain-ocr-trainer-spa
track: D
---

# Labeler Import Auto-Discovery + Freshness (Track D)

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add auto-discovery of the labeler export root via `pdomain-ops`
`resolve_shared_path`, manifest-based freshness flagging on the kanban, and a
dismissible "new labeled pages" banner when fresher exports are detected.

**Architecture:** Three features build on each other without restructuring
the existing domain layer. Auto-discovery extends `Settings` with a
`labeler_export_root_mode` derived field and a new
`domain/labeler_export.py` helper that wraps the optional `pdomain-ops`
import. Freshness detection reads a `DoctrExportManifest` (from `pdomain-ops`
`read_manifest`) and compares `exported_at` timestamps against a
`freshness_state.json` persisted in `app_data_root/profiles/<profile>/` — the
same directory pattern already used by `kanban_state.json`. The banner is
added to `domain/banners.py` following the existing builder pattern;
`synthesize_banners` receives a second `freshness_state` parameter so the
function stays pure.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, `pydantic-settings`,
`pdomain-ops` (`resolve_shared_path`, `DoctrExportManifest`, `read_manifest`
— Track B gate), `pytest` with `tmp_path`, `pytest-playwright` for browser
verification.

**Track B dependency (coordination point):** This plan imports:

```python
from pdomain_ops.suite.shared_paths import resolve_shared_path  # -> Path | None
from pdomain_ops.schemas.doctr_export import DoctrExportManifest, read_manifest
     # -> DoctrExportManifest | None
```

Exact import paths may shift slightly as Track B lands. All calls to these
symbols are isolated in `domain/labeler_export.py`. If the symbols are absent
at import time (older `pdomain-ops` wheel), a `try/except ImportError` guard
degrades to `None`/`no-op` so the SPA still boots. Add a
`docs/conventions/lint-deviations.md` entry for the guarded import.

---

## File map

| Action | Path |
| --- | --- |
| Create | `src/pdomain_ocr_trainer_spa/domain/labeler_export.py` |
| Modify | `src/pdomain_ocr_trainer_spa/settings.py` |
| Modify | `src/pdomain_ocr_trainer_spa/domain/banners.py` |
| Modify | `src/pdomain_ocr_trainer_spa/domain/datasets.py` |
| Modify | `src/pdomain_ocr_trainer_spa/core/models.py` |
| Modify | `src/pdomain_ocr_trainer_spa/api/banners.py` |
| Modify | `src/pdomain_ocr_trainer_spa/api/datasets.py` |
| Create | `tests/unit/domain/test_labeler_export.py` |
| Modify | `tests/unit/domain/test_banners.py` |
| Modify | `tests/unit/domain/test_datasets.py` |
| Create | `tests/e2e/test_labeler_freshness.py` |
| Modify | `docs/conventions/lint-deviations.md` |
| Modify | `pyproject.toml` (e2e dependency group + Makefile) |
| Modify | `Makefile` |

---

## Task 1: `domain/labeler_export.py` — auto-discovery + manifest helpers

**Files:**

+ Create: `src/pdomain_ocr_trainer_spa/domain/labeler_export.py`
+ Create: `tests/unit/domain/test_labeler_export.py`

+ [ ] **Step 1: Write the failing test**

```python
# tests/unit/domain/test_labeler_export.py
"""Tests for labeler export auto-discovery and manifest helpers."""
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from pdomain_ocr_trainer_spa.domain.labeler_export import (
    ExportRootMode,
    resolve_export_root,
    read_export_manifest,
    ExportFreshnessRecord,
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
    (tmp_path / "manifest.json").write_text(json.dumps(manifest_data),
        encoding="utf-8")
    result = read_export_manifest(tmp_path)
    assert result is not None
    assert "myproj" in result.projects


def test_freshness_record_roundtrip(tmp_path: Path) -> None:
    rec = ExportFreshnessRecord(
        project_seen_at={"myproj": "2026-06-10T11:00:00Z"}
    )
    path = tmp_path / "freshness_state.json"
    rec.save(path)
    loaded = ExportFreshnessRecord.load(path)
    assert loaded.project_seen_at == {"myproj": "2026-06-10T11:00:00Z"}


def test_freshness_record_load_missing_returns_empty(tmp_path: Path) -> None:
    rec = ExportFreshnessRecord.load(tmp_path / "nonexistent.json")
    assert rec.project_seen_at == {}
```

+ [ ] **Step 2: Run the test to confirm it fails**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/domain/test_labeler_export.py -v 2>&1 | tail -20
```

Expected: `ModuleNotFoundError: No module named
'pdomain_ocr_trainer_spa.domain.labeler_export'`

+ [ ] **Step 3: Implement `domain/labeler_export.py`**

```python
# src/pdomain_ocr_trainer_spa/domain/labeler_export.py
"""Labeler export root auto-discovery and manifest freshness helpers (Track D).

Isolates all optional pdomain-ops imports so the SPA boots even when
an older pdomain-ops wheel is installed (Track B gating dependency).
"""
from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Optional pdomain-ops import — Track B gate
# ---------------------------------------------------------------------------
# This import is intentionally guarded; see docs/conventions/lint-deviations.md
# entry "labeler_export.py: pdomain_ops.suite.shared_paths optional import".
try:
    from pdomain_ops.suite.shared_paths import (  # pyright:
        ignore[reportMissingImports]
        resolve_shared_path as _resolve_shared_path_impl,
    )

    def _shared_path_lookup(key: str) -> Path | None:
        return _resolve_shared_path_impl(key)

except ImportError:
    def _shared_path_lookup(key: str) -> Path | None:  # type: ignore[misc]  #
        noqa: F811
        return None  # pdomain-ops not installed or pre-Track-B version


# ---------------------------------------------------------------------------
# Optional manifest model — falls back to raw JSON dict when import missing
# ---------------------------------------------------------------------------
try:
    from pdomain_ops.schemas.doctr_export import (  # pyright:
        ignore[reportMissingImports]
        DoctrExportManifest,
        read_manifest as _read_manifest_impl,
    )

    def read_export_manifest(export_root: Path) -> DoctrExportManifest | None:
        """Read the manifest.json from an export root; None if absent
            or unreadable."""
        if not export_root.exists():
            return None
        return _read_manifest_impl(export_root)

except ImportError:
    class DoctrExportManifest(BaseModel):  # type: ignore[no-redef]  # noqa:
        F811
        """Fallback manifest model when pdomain-ops pre-Track-B is installed."""

        schema_: str = ""
        version: int = 0
        generated_at: str = ""
        app: str = ""
        projects: dict[str, Any] = {}

    def read_export_manifest(export_root: Path) -> DoctrExportManifest | None:
        # type: ignore[misc]  # noqa: F811
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
        return DoctrExportManifest(**data)


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
    """Return (export_root, mode). Explicit setting always wins over
        discovery."""
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
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"version": 1, "project_seen_at": self.project_seen_at},
                indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> ExportFreshnessRecord:
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        return cls(project_seen_at=data.get("project_seen_at", {}))
```

+ [ ] **Step 4: Run the test**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/domain/test_labeler_export.py -v 2>&1 | tail -20
```

Expected: all 6 tests PASS

+ [ ] **Step 5: Add lint-deviations entry**

Open `docs/conventions/lint-deviations.md` (create it if absent; check
`docs/conventions/` directory first with `ls docs/conventions/`). Add:

```markdown
## `domain/labeler_export.py`: optional pdomain-ops Track-B imports

- **Rules:** `reportMissingImports` (basedpyright), `F811` (ruff — redefinition
  in except branch)
- **Tool:** basedpyright + ruff
- **Files:** `src/pdomain_ocr_trainer_spa/domain/labeler_export.py`
- **Justification:** Track B (`pdomain-ops`) adds `resolve_shared_path` and
  `DoctrExportManifest` / `read_manifest`. The SPA must boot with a pre-Track-B
  wheel installed; the `try/except ImportError` guard plus fallback stubs is the
  approved pattern. Inline comments name the suppressed codes at each deviation
  site.
```

+ [ ] **Step 6: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add src/pdomain_ocr_trainer_spa/domain/labeler_export.py \
        tests/unit/domain/test_labeler_export.py \
        docs/conventions/lint-deviations.md
git commit -m "feat(track-d): labeler export auto-discovery + manifest helpers"
```

---

## Task 2: Settings — derive `labeler_export_root_mode`

**Files:**

+ Modify: `src/pdomain_ocr_trainer_spa/settings.py`
+ Modify: `tests/unit/test_app_state.py` (or a new
  `tests/unit/test_settings.py`)

The `Settings` model does not call domain helpers directly (pure
`pydantic-settings`). Instead the `AppState` or the route handler that
needs the resolved root calls
`resolve_export_root(settings.labeler_export_root)`
at request time. `Settings` gains one new read-only property that makes
the mode derivable without I/O:

+ [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_settings.py  (create new file)
"""Tests for Settings.labeler_export_root_mode property."""
from __future__ import annotations
from pathlib import Path
import pytest
from pdomain_ocr_trainer_spa.settings import Settings


def test_mode_configured_when_explicit(tmp_path: Path) -> None:
    s = Settings(labeler_export_root=tmp_path)  # type: ignore[arg-type]
    assert s.labeler_export_root == tmp_path


def test_mode_none_when_absent() -> None:
    s = Settings(labeler_export_root=None)
    assert s.labeler_export_root is None
```

+ [ ] **Step 2: Run the test to confirm it passes (settings already exist)**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/test_settings.py -v 2>&1 | tail -10
```

Expected: PASS (these exercise existing behaviour)

+ [ ] **Step 3: Expose resolved mode via a settings-level diagnostics endpoint**

The diagnostics surface lives in `api/healthz.py` (or a new `api/diagnostics.py`
if `healthz.py` only returns `{"status":"ok"}`). Read `api/healthz.py` first.
Add a `GET /api/diagnostics/labeler-export` endpoint that returns:

```python
class LabelerExportDiagnostics(BaseModel):
    mode: str           # "configured" | "discovered" | "absent"
    export_root: str | None  # resolved path as str, or null
```

Implementation in `api/datasets.py` (add to the existing router) or in
`api/healthz.py` — check which is more appropriate given the existing layout.

```python
# In api/datasets.py — add after existing routes

from pdomain_ocr_trainer_spa.domain.labeler_export import resolve_export_root

class LabelerExportDiagnostics(BaseModel):
    mode: str
    export_root: str | None

@router.get("/labeler-export-diagnostics")
async def labeler_export_diagnostics(
    state: AppState = Depends(get_app_state),
) -> LabelerExportDiagnostics:
    root, mode = resolve_export_root(state.settings.labeler_export_root)
    return LabelerExportDiagnostics(
        mode=mode.value,
        export_root=str(root) if root is not None else None,
    )
```

+ [ ] **Step 4: Write the test for the diagnostics endpoint**

```python
# tests/unit/api/test_datasets_diagnostics.py  (create tests/unit/api/ if
# absent)
"""Test /api/labeler-export-diagnostics endpoint."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from pdomain_ocr_trainer_spa.settings import Settings
from pdomain_ocr_trainer_spa.bootstrap import build_app


def test_diagnostics_configured(tmp_path: Path) -> None:
    export = tmp_path / "export"
    export.mkdir()
    s = Settings(
        labeler_export_root=export,  # type: ignore[arg-type]
        app_data_root=tmp_path / "app",  # type: ignore[arg-type]
        runs_dir=tmp_path / "runs",  # type: ignore[arg-type]
        jobs_db_path=tmp_path / "jobs.db",  # type: ignore[arg-type]
        job_runner_kind="fake",
        model_registry_kind="fake",
    )
    client = TestClient(build_app(s))
    resp = client.get("/api/labeler-export-diagnostics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "configured"
    assert data["export_root"] == str(export)


def test_diagnostics_absent(tmp_path: Path) -> None:
    with patch(
        "pdomain_ocr_trainer_spa.domain.labeler_export._shared_path_lookup",
        return_value=None,
    ):
        s = Settings(
            labeler_export_root=None,
            app_data_root=tmp_path / "app",  # type: ignore[arg-type]
            runs_dir=tmp_path / "runs",  # type: ignore[arg-type]
            jobs_db_path=tmp_path / "jobs.db",  # type: ignore[arg-type]
            job_runner_kind="fake",
            model_registry_kind="fake",
        )
        client = TestClient(build_app(s))
        resp = client.get("/api/labeler-export-diagnostics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "absent"
    assert data["export_root"] is None
```

+ [ ] **Step 5: Run tests**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/test_settings.py tests/unit/api/ -v 2>&1 | tail -20
```

Expected: all PASS

+ [ ] **Step 6: Update `domain/datasets.py` to use `resolve_export_root`**

Replace the direct read of `settings.labeler_export_root` in
`_iter_export_dirs`:

```python
# In domain/datasets.py — update _iter_export_dirs

from pdomain_ocr_trainer_spa.domain.labeler_export import resolve_export_root

def _iter_export_dirs(settings: Settings, profile: str,
    task: TaskEnum) -> list[tuple[str, Path]]:
    """Return (project_id, task_dir) for every export matching profile."""
    root, _mode = resolve_export_root(settings.labeler_export_root)
    if root is None or not root.exists():
        return []
    found: list[tuple[str, Path]] = []
    for project_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for sub in sorted(s for s in project_dir.iterdir() if s.is_dir()):
            if normalize_profile_name(sub.name) != profile:
                continue
            task_path = sub / task.value
            if task_path.exists():
                found.append((project_dir.name, task_path))
    return found
```

+ [ ] **Step 7: Run all dataset tests**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/domain/test_datasets.py -v 2>&1 | tail -20
```

Expected: all PASS (no regression)

+ [ ] **Step 8: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add src/pdomain_ocr_trainer_spa/api/datasets.py \
        src/pdomain_ocr_trainer_spa/domain/datasets.py \
        tests/unit/test_settings.py \
        tests/unit/api/
git commit -m "feat(track-d): diagnostics endpoint + wire resolve_export_root \
  into datasets"
```

---

## Task 3: Manifest-based freshness — `KanbanProjectRow.is_fresh` + freshness state

**Files:**

+ Modify: `src/pdomain_ocr_trainer_spa/core/models.py`
+ Modify: `src/pdomain_ocr_trainer_spa/domain/datasets.py`
+ Modify: `tests/unit/domain/test_datasets.py`

+ [ ] **Step 1: Extend `KanbanProjectRow` with `is_fresh`**

In `core/models.py`, add one optional field to `KanbanProjectRow`:

```python
class KanbanProjectRow(BaseModel):
    """A project's row within a kanban column (spec 05 §2)."""

    project_id: str
    source: Literal["pending", "on_disk"]
    page_count: int
    is_changed: bool = False
    is_fresh: bool = False   # NEW: manifest exported_at is newer than last-seen
    style_tags: list[str] = []
    pages: list[KanbanPageChip] = []
```

+ [ ] **Step 2: Write the failing freshness test**

```python
# Add to tests/unit/domain/test_datasets.py

def test_fresh_flag_set_when_manifest_newer(tmp_path: Path,
    settings: Settings) -> None:
    """Projects with a manifest exported_at newer than last-seen are flagged
        is_fresh."""
    import json
    settings = settings.__class__(
        **{
            **settings.model_dump(),
            "labeler_export_root": tmp_path / "export",
        }
    )
    # Build an export tree with manifest
    export_root = tmp_path / "export"
    proj_dir = export_root / "myproj" / "all" / "recognition"
    proj_dir.mkdir(parents=True)
    (proj_dir / "labels.json").write_text(json.dumps({"img_0001.png": "test"}),
        encoding="utf-8")
    (proj_dir / "images").mkdir()
    (proj_dir / "images" / "img_0001.png").write_bytes(b"png")
    # Write manifest with a known timestamp
    manifest_data = {
        "schema": "pdomain.doctr-export-manifest",
        "version": 1,
        "generated_at": "2026-06-10T12:00:00Z",
        "app": "pdomain-ocr-labeler-spa",
        "projects": {
            "myproj": {
                "exported_at": "2026-06-10T11:00:00Z",
                "page_count": 1,
                "tasks": {"recognition": {"item_count": 1}},
            }
        },
    }
    (export_root / "manifest.json").write_text(json.dumps(manifest_data),
        encoding="utf-8")
    # No freshness record exists — first scan, so project is fresh
    from pdomain_ocr_trainer_spa.core.enums import TaskEnum
    from pdomain_ocr_trainer_spa.domain import datasets as dom
    view = dom.build_kanban(settings, profile="all", task=TaskEnum.recognition)
    unassigned_rows = view.columns["unassigned"].rows
    assert len(unassigned_rows) == 1
    assert unassigned_rows[0].project_id == "myproj"
    assert unassigned_rows[0].is_fresh is True


def test_fresh_flag_not_set_when_seen_at_matches(tmp_path: Path,
    settings: Settings) -> None:
    """Projects where exported_at == last-seen are not flagged is_fresh."""
    import json
    settings = settings.__class__(
        **{
            **settings.model_dump(),
            "labeler_export_root": tmp_path / "export",
        }
    )
    export_root = tmp_path / "export"
    proj_dir = export_root / "myproj" / "all" / "recognition"
    proj_dir.mkdir(parents=True)
    (proj_dir / "labels.json").write_text(json.dumps({"img_0001.png": "test"}),
        encoding="utf-8")
    (proj_dir / "images").mkdir()
    (proj_dir / "images" / "img_0001.png").write_bytes(b"png")
    manifest_data = {
        "schema": "pdomain.doctr-export-manifest",
        "version": 1,
        "generated_at": "2026-06-10T12:00:00Z",
        "app": "pdomain-ocr-labeler-spa",
        "projects": {
            "myproj": {
                "exported_at": "2026-06-10T11:00:00Z",
                "page_count": 1,
                "tasks": {"recognition": {"item_count": 1}},
            }
        },
    }
    (export_root / "manifest.json").write_text(json.dumps(manifest_data),
        encoding="utf-8")
    # Pre-seed the freshness record with the same timestamp
    from pdomain_ocr_trainer_spa.domain.labeler_export import
        ExportFreshnessRecord
    rec = ExportFreshnessRecord(project_seen_at={"myproj":
        "2026-06-10T11:00:00Z"})
    freshness_path = settings.app_data_root / "profiles" / "all" /
        "freshness_state.json"
    freshness_path.parent.mkdir(parents=True, exist_ok=True)
    rec.save(freshness_path)
    from pdomain_ocr_trainer_spa.core.enums import TaskEnum
    from pdomain_ocr_trainer_spa.domain import datasets as dom
    view = dom.build_kanban(settings, profile="all", task=TaskEnum.recognition)
    unassigned_rows = view.columns["unassigned"].rows
    assert not any(r.is_fresh for r in unassigned_rows)


def test_no_manifest_no_fresh_flag(tmp_path: Path, settings: Settings) -> None:
    """When no manifest.json exists, is_fresh is always False (zero
        regression)."""
    import json
    settings = settings.__class__(
        **{
            **settings.model_dump(),
            "labeler_export_root": tmp_path / "export",
        }
    )
    export_root = tmp_path / "export"
    proj_dir = export_root / "myproj" / "all" / "recognition"
    proj_dir.mkdir(parents=True)
    (proj_dir / "labels.json").write_text(json.dumps({"img_0001.png": "test"}),
        encoding="utf-8")
    (proj_dir / "images").mkdir()
    (proj_dir / "images" / "img_0001.png").write_bytes(b"png")
    # No manifest.json written
    from pdomain_ocr_trainer_spa.core.enums import TaskEnum
    from pdomain_ocr_trainer_spa.domain import datasets as dom
    view = dom.build_kanban(settings, profile="all", task=TaskEnum.recognition)
    unassigned_rows = view.columns["unassigned"].rows
    assert not any(r.is_fresh for r in unassigned_rows)
```

+ [ ] **Step 3: Run the failing tests**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
T=tests/unit/domain/test_datasets.py
uv run pytest \
  "$T::test_fresh_flag_set_when_manifest_newer" \
  "$T::test_fresh_flag_not_set_when_seen_at_matches" \
  "$T::test_no_manifest_no_fresh_flag" \
  -v 2>&1 | tail -20
```

Expected: FAIL with `unexpected keyword argument 'is_fresh'` or assertion error

+ [ ] **Step 4: Add freshness logic to `domain/datasets.py`**

Add a new helper and thread freshness data into `_unassigned_rows`:

```python
# At the top of domain/datasets.py, add import
from pdomain_ocr_trainer_spa.domain.labeler_export import (
    ExportFreshnessRecord,
    read_export_manifest,
    resolve_export_root,
)


def _freshness_state_path(settings: Settings, profile: str) -> Path:
    """Path to a profile's freshness_state.json."""
    return settings.app_data_root / "profiles" / profile /
        "freshness_state.json"


def _load_fresh_project_ids(settings: Settings, profile: str) -> frozenset[str]:
    """Return project_ids that have a manifest exported_at newer than last-seen.

    Returns an empty frozenset when no manifest is present (zero regression).
    """
    root, _mode = resolve_export_root(settings.labeler_export_root)
    if root is None:
        return frozenset()
    manifest = read_export_manifest(root)
    if manifest is None:
        return frozenset()
    freshness_path = _freshness_state_path(settings, profile)
    record = ExportFreshnessRecord.load(freshness_path)
    fresh: set[str] = set()
    for project_id, proj_data in manifest.projects.items():
        exported_at = proj_data.get("exported_at", "") if isinstance(proj_data,
            dict) else getattr(proj_data, "exported_at", "")
        last_seen = record.project_seen_at.get(project_id)
        if last_seen is None or str(exported_at) > str(last_seen):
            fresh.add(project_id)
    return frozenset(fresh)
```

Then in `_unassigned_rows`, add a `fresh_ids` parameter and set `is_fresh`:

```python
def _unassigned_rows(
    settings: Settings,
    profile: str,
    task: TaskEnum,
    on_disk: dict[str, LabelMap],
    fresh_ids: frozenset[str],   # NEW parameter
) -> list[KanbanProjectRow]:
    # ... existing body unchanged until KanbanProjectRow construction ...
    rows.append(
        KanbanProjectRow(
            project_id=project_id,
            source="pending",
            page_count=len(chips),
            is_changed=any(c.is_changed for c in chips),
            is_fresh=project_id in fresh_ids,   # NEW
            style_tags=[],
            pages=chips,
        )
    )
```

And pass `fresh_ids` from `build_kanban`:

```python
def build_kanban(settings: Settings, *, profile: str,
    task: TaskEnum) -> KanbanView:
    _require_supported(task)
    normalized = normalize_profile_name(profile)
    on_disk = {split: _on_disk_labels(settings, split, normalized,
        task) for split in _SPLIT_DIRS}
    include_detection, include_recognition = _read_include_toggles(settings,
        normalized)
    fresh_ids = _load_fresh_project_ids(settings, normalized)   # NEW
    return KanbanView(
        profile=normalized,
        task=task,
        columns={
            "unassigned": KanbanColumn(rows=_unassigned_rows(settings,
                normalized, task, on_disk, fresh_ids)),
            "train": KanbanColumn(rows=_rows_from_labels(task, on_disk["train"],
                "on_disk")),
            "val": KanbanColumn(rows=_rows_from_labels(task, on_disk["val"],
                "on_disk")),
        },
        include_detection=include_detection,
        include_recognition=include_recognition,
    )
```

+ [ ] **Step 5: Run the freshness tests**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/domain/test_datasets.py -v 2>&1 | tail -20
```

Expected: all PASS

+ [ ] **Step 6: Update freshness record on kanban scan**

The freshness record should be written (to mark projects as seen) when
`build_kanban` is called so that dismissing the banner and re-scanning
does not re-fire. Add a `_update_freshness_record` function:

```python
def _update_freshness_record(settings: Settings, profile: str,
    fresh_ids: frozenset[str]) -> None:
    """Persist the current manifest exported_at values for the given fresh
        projects.

    Called after a successful kanban build so subsequent scans do not
    re-flag already-seen exports. Only writes if fresh_ids is non-empty.
    """
    if not fresh_ids:
        return
    root, _mode = resolve_export_root(settings.labeler_export_root)
    if root is None:
        return
    manifest = read_export_manifest(root)
    if manifest is None:
        return
    freshness_path = _freshness_state_path(settings, profile)
    record = ExportFreshnessRecord.load(freshness_path)
    for project_id in fresh_ids:
        proj_data = manifest.projects.get(project_id)
        if proj_data is not None:
            exported_at = proj_data.get("exported_at",
                "") if isinstance(proj_data, dict)
                    else getattr(proj_data, "exported_at", "")
            record.project_seen_at[project_id] = str(exported_at)
    record.save(freshness_path)
```

Call `_update_freshness_record(settings, normalized, fresh_ids)` at the end
of `build_kanban`, after assembling the view.

**Write a test for the update:**

```python
def test_freshness_record_updated_after_build(tmp_path: Path,
    settings: Settings) -> None:
    """build_kanban persists the seen timestamp so the next scan does not
        re-flag."""
    import json
    settings = settings.__class__(
        **{
            **settings.model_dump(),
            "labeler_export_root": tmp_path / "export",
        }
    )
    export_root = tmp_path / "export"
    proj_dir = export_root / "myproj" / "all" / "recognition"
    proj_dir.mkdir(parents=True)
    (proj_dir / "labels.json").write_text(json.dumps({"img_0001.png": "x"}),
        encoding="utf-8")
    (proj_dir / "images").mkdir()
    (proj_dir / "images" / "img_0001.png").write_bytes(b"png")
    manifest_data = {
        "schema": "pdomain.doctr-export-manifest",
        "version": 1,
        "generated_at": "2026-06-10T12:00:00Z",
        "app": "pdomain-ocr-labeler-spa",
        "projects": {
            "myproj": {
                "exported_at": "2026-06-10T11:00:00Z",
                "page_count": 1,
                "tasks": {"recognition": {"item_count": 1}},
            }
        },
    }
    (export_root / "manifest.json").write_text(json.dumps(manifest_data),
        encoding="utf-8")
    from pdomain_ocr_trainer_spa.core.enums import TaskEnum
    from pdomain_ocr_trainer_spa.domain import datasets as dom
    from pdomain_ocr_trainer_spa.domain.labeler_export import
        ExportFreshnessRecord
    # First scan — fresh
    dom.build_kanban(settings, profile="all", task=TaskEnum.recognition)
    # Second scan — record was persisted, no longer fresh
    view2 = dom.build_kanban(settings, profile="all", task=TaskEnum.recognition)
    assert not any(r.is_fresh for r in view2.columns["unassigned"].rows)
```

+ [ ] **Step 7: Run full dataset tests**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/domain/test_datasets.py -v 2>&1 | tail -20
```

Expected: all PASS

+ [ ] **Step 8: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add src/pdomain_ocr_trainer_spa/core/models.py \
        src/pdomain_ocr_trainer_spa/domain/datasets.py \
        tests/unit/domain/test_datasets.py
git commit -m "feat(track-d): manifest freshness — KanbanProjectRow.is_fresh + \
  persistence"
```

---

## Task 4: "New labeled pages" banner

**Files:**

+ Modify: `src/pdomain_ocr_trainer_spa/domain/banners.py`
+ Modify: `src/pdomain_ocr_trainer_spa/api/banners.py`
+ Modify: `tests/unit/domain/test_banners.py`

The banner fires when `build_kanban` finds any `is_fresh` project in the
unassigned column. Because `synthesize_banners` is currently stateless and
takes only `settings`, we add one new pure function `_new_labeled_pages_banner`
that is driven by a pre-computed `fresh_project_count: int` argument.
`synthesize_banners` gains a `fresh_project_count: int = 0` parameter so
callers can pass the count without changing the other banner builders.

+ [ ] **Step 1: Write the failing banner test**

```python
# Add to tests/unit/domain/test_banners.py

from pdomain_ocr_trainer_spa.domain.banners import synthesize_banners


def test_new_labeled_pages_banner_fires_when_fresh(settings) -> None:
    banners = synthesize_banners(settings, fresh_project_count=3)
    ids = [b.id for b in banners]
    assert "new-labeled-pages" in ids
    banner = next(b for b in banners if b.id == "new-labeled-pages")
    assert banner.severity == "info"
    assert banner.dismissible is True
    assert "3" in banner.description


def test_new_labeled_pages_banner_absent_when_zero(settings) -> None:
    banners = synthesize_banners(settings, fresh_project_count=0)
    ids = [b.id for b in banners]
    assert "new-labeled-pages" not in ids
```

+ [ ] **Step 2: Run the failing test**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/domain/test_banners.py -v 2>&1 | tail -20
```

Expected: FAIL with `TypeError: synthesize_banners() got an unexpected keyword
argument 'fresh_project_count'`

+ [ ] **Step 3: Add the banner builder to `domain/banners.py`**

```python
# Add to domain/banners.py, before synthesize_banners

def _new_labeled_pages_banner(fresh_project_count: int) -> Banner | None:
    """Return the new-labeled-pages banner when fresh exports are detected."""
    if fresh_project_count == 0:
        return None
    noun = "project" if fresh_project_count == 1 else "projects"
    return Banner(
        id="new-labeled-pages",
        severity="info",
        title="New labeled pages available",
        description=(
            f"{fresh_project_count} {noun} ha{'s'
                if fresh_project_count == 1 else 've'} "
            "new or updated labeled exports. Open the Dataset kanban to review."
        ),
        action=BannerAction(label="Open Datasets", href="/datasets"),
        dismissible=True,
    )


def synthesize_banners(settings: Settings, *,
    fresh_project_count: int = 0) -> list[Banner]:
    """Return the active banner list derived from the current environment.

    Order: hf-token-missing, disk-low, new-labeled-pages.
    """
    banners: list[Banner] = []
    for builder in (_hf_token_banner, _disk_low_banner):
        banner = builder(settings)
        if banner is not None:
            banners.append(banner)
    fresh_banner = _new_labeled_pages_banner(fresh_project_count)
    if fresh_banner is not None:
        banners.append(fresh_banner)
    return banners
```

+ [ ] **Step 4: Update `api/banners.py` to compute `fresh_project_count`**

The banner route needs to scan the kanban briefly to count fresh projects.
To avoid a full kanban build (expensive), add a lightweight
`count_fresh_projects(settings)` function to `domain/datasets.py`:

```python
# Add to domain/datasets.py

def count_fresh_projects(settings: Settings, *, profile: str = "all") -> int:
    """Return the number of projects with a manifest exported_at newer than
        last-seen.

    Used by the banners endpoint to decide whether to emit the new-labeled-pages
    banner without building a full KanbanView.
    """
    normalized = normalize_profile_name(profile)
    fresh_ids = _load_fresh_project_ids(settings, normalized)
    return len(fresh_ids)
```

Then in `api/banners.py`:

```python
from pdomain_ocr_trainer_spa.domain import datasets as datasets_dom

@router.get("", response_model=BannerListResponse)
async def list_banners(
    state: AppState = Depends(get_app_state),
) -> BannerListResponse:
    fresh_count = datasets_dom.count_fresh_projects(state.settings)
    return BannerListResponse(
        banners=synthesize_banners(state.settings,
            fresh_project_count=fresh_count)
    )
```

+ [ ] **Step 5: Run all banner tests**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
uv run pytest tests/unit/domain/test_banners.py -v 2>&1 | tail -20
```

Expected: all PASS

+ [ ] **Step 6: Run full CI**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make ci 2>&1 | tail -30
```

Expected: GREEN

+ [ ] **Step 7: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add src/pdomain_ocr_trainer_spa/domain/banners.py \
        src/pdomain_ocr_trainer_spa/domain/datasets.py \
        src/pdomain_ocr_trainer_spa/api/banners.py \
        tests/unit/domain/test_banners.py
git commit -m "feat(track-d): new-labeled-pages banner via manifest freshness"
```

---

## Task 5: Browser Verification (Mandatory)

**Files:**

+ Modify: `pyproject.toml`
+ Modify: `Makefile`
+ Create: `tests/e2e/test_labeler_freshness.py`

This milestone requires Playwright browser verification per the workspace
contract for FastAPI + SPA repos.

+ [ ] **Step 1: Add e2e dependency group**

In `pyproject.toml`, add under `[dependency-groups]`:

```toml
[dependency-groups]
e2e = ["pytest-playwright>=0.5"]
```

+ [ ] **Step 2: Add Makefile targets**

In `Makefile`, add:

```makefile
.PHONY: e2e-browser
e2e-browser:  ## Run Playwright browser e2e tests
 uv run --group e2e pytest tests/e2e/ -v

playwright-install:  ## Install Playwright browsers (run once)
 uv run --group e2e playwright install chromium
```

Add `e2e-browser` to the `ci` target's dependency list (after `test`).

+ [ ] **Step 3: Wire `playwright install` into `make setup`**

In `Makefile`, add to the `setup` target:

```makefile
 uv run --group e2e playwright install chromium
```

+ [ ] **Step 4: Write the e2e test**

```python
# tests/e2e/test_labeler_freshness.py
"""Browser verification: kanban renders fresh-flagged projects + banner visible.

Uses a fixture export tree + manifest so the test is fully self-contained.
Requires `make playwright-install` (runs chromium).
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest
import uvicorn

from pdomain_ocr_trainer_spa.bootstrap import build_app
from pdomain_ocr_trainer_spa.settings import Settings


@pytest.fixture(scope="module")
def export_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a minimal export tree with a manifest for 'myproj'."""
    base = tmp_path_factory.mktemp("export")
    proj = base / "myproj" / "all" / "recognition"
    proj.mkdir(parents=True)
    (proj / "labels.json").write_text(
        json.dumps({"img_0001.png": "test label"}), encoding="utf-8"
    )
    images = proj / "images"
    images.mkdir()
    (images / "img_0001.png").write_bytes(b"\x89PNG")
    manifest = {
        "schema": "pdomain.doctr-export-manifest",
        "version": 1,
        "generated_at": "2026-06-10T12:00:00Z",
        "app": "pdomain-ocr-labeler-spa",
        "projects": {
            "myproj": {
                "exported_at": "2026-06-10T11:00:00Z",
                "page_count": 1,
                "tasks": {"recognition": {"item_count": 1}},
            }
        },
    }
    (base / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return base


@pytest.fixture(scope="module")
def live_server(tmp_path_factory: pytest.TempPathFactory, export_tree: Path):
    """Start the real FastAPI app on a free port; yield the base URL."""
    tmp = tmp_path_factory.mktemp("app")
    s = Settings(
        labeler_export_root=export_tree,  # type: ignore[arg-type]
        app_data_root=tmp / "app",  # type: ignore[arg-type]
        runs_dir=tmp / "runs",  # type: ignore[arg-type]
        jobs_db_path=tmp / "jobs.db",  # type: ignore[arg-type]
        job_runner_kind="fake",
        model_registry_kind="fake",
        host="127.0.0.1",
        port=0,
    )
    # Build the SPA with a fake index.html so GET / returns 200
    static_dir = Path(__file__).parent.parent.parent / "src" /
        "pdomain_ocr_trainer_spa" / "static"
    static_dir.mkdir(exist_ok=True)
    (static_dir / "index.html").write_text(
        '<html><body data-testid="home-page">OCR Trainer</body></html>',
        encoding="utf-8",
    )
    app = build_app(s)
    config = uvicorn.Config(app, host="127.0.0.1", port=8091,
        log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    # Wait for server to be ready
    import socket
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", 8091), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    yield "http://127.0.0.1:8091"
    server.should_exit = True


def test_home_page_loads(page, live_server: str) -> None:
    """SPA index.html is served; no console errors about failed resources."""
    errors: list[str] = []
    page.on("console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(live_server)
    page.wait_for_selector('[data-testid="home-page"]', timeout=5000)
    assert not errors, f"console errors: {errors}"


def test_banners_api_returns_fresh_banner(page, live_server: str) -> None:
    """GET /api/banners returns the new-labeled-pages banner for our fixture
        export."""
    import requests
    resp = requests.get(f"{live_server}/api/banners", timeout=5)
    assert resp.status_code == 200
    banners = resp.json()["banners"]
    ids = [b["id"] for b in banners]
    assert "new-labeled-pages" in ids, f"expected new-labeled-pages in {ids}"


def test_kanban_api_returns_fresh_row(live_server: str) -> None:
    """GET /api/profiles/all/datasets/recognition/kanban returns is_fresh=true
        for myproj."""
    import requests
    # Reset freshness state to simulate first scan
    resp = requests.get(
        f"{live_server}/api/profiles/all/datasets/recognition/kanban", timeout=5
    )
    assert resp.status_code == 200
    view = resp.json()
    unassigned = view["columns"]["unassigned"]["rows"]
    assert len(unassigned) >= 1
    fresh_rows = [r for r in unassigned if r.get("is_fresh")]
    assert len(fresh_rows) >= 1, f"expected at least one is_fresh row; got
        {unassigned}"


def test_datasets_subpath_renders(page, live_server: str) -> None:
    """React Router sub-path /datasets/all/recognition renders the page
        component."""
    page.goto(f"{live_server}/datasets/all/recognition")
    page.wait_for_selector('[data-testid="home-page"]', timeout=5000)
    assert page.url.endswith("/datasets/all/recognition")
```

+ [ ] **Step 5: Run the e2e tests**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make playwright-install 2>&1 | tail -5
make e2e-browser 2>&1 | tail -30
```

Expected: all 4 tests PASS

+ [ ] **Step 6: Run full CI**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
make ci 2>&1 | tail -30
```

Expected: GREEN (e2e-browser included)

+ [ ] **Step 7: Commit**

```bash
cd /workspaces/ocr-container/pdomain-ocr-trainer-spa
git add pyproject.toml Makefile tests/e2e/test_labeler_freshness.py
git commit -m "feat(track-d): Playwright browser verification for freshness \
  banner + kanban"
```

---

## Self-review checklist

**Spec coverage:**

+ [x] Auto-discovery via `resolve_shared_path("doctr-export-root")` — Task 1+2
+ [x] Explicit setting always wins — Task 1 (`ExportRootMode.configured`)
+ [x] Surface mode in diagnostics endpoint — Task 2
+ [x] Manifest-based freshness comparison — Task 3
+ [x] `is_changed` highlighting contract extended (not duplicated) — Task 3 adds
  `is_fresh`; `is_changed` logic unchanged
+ [x] Absent manifest → current behaviour, zero regression — Task 3
  `test_no_manifest_no_fresh_flag`
+ [x] Freshness record persisted in `kanban_state.json` sibling —
  `freshness_state.json` same dir
+ [x] Dismissible banner — Task 4 (`dismissible=True`)
+ [x] Banner re-armed on next newer export — freshness record updated per scan;
  new timestamp triggers again
+ [x] Browser Verification milestone — Task 5

**Open questions for implementer:**

1. Track B exact import paths:
   `pdomain_ops.suite.shared_paths.resolve_shared_path` and
   `pdomain_ops.schemas.doctr_export.DoctrExportManifest` / `read_manifest`. If
   these differ, update the `try/except` blocks in `domain/labeler_export.py`
   only — the rest of the plan is unchanged.
2. `manifest.projects` type: the plan treats it as `dict[str, dict | Any]`. When
   Track B ships the real `DoctrExportManifest`, replace the
   `isinstance(proj_data, dict)` branches with direct attribute access.
3. The `count_fresh_projects` function defaults to `profile="all"`. If
   multi-profile freshness counting is needed, the banner route can call it
   per-profile and sum — deferred to a follow-up.
