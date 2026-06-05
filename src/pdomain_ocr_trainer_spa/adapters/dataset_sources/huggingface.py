"""HuggingFace IDatasetSource implementation (spec 09 §3-§4, M10).

The public surface used by the SPA web process (torch-free):
  - ``HuggingFaceDatasetSource.preview``   — thin preview of ≤50 rows
  - ``HuggingFaceDatasetSource.fetch_to_local`` — materialize into hf_cache_dir

Heavy imports (``huggingface_hub``, ``datasets``) are done lazily inside
methods so this module still imports clean in environments without them.

Authentication: the caller must supply the HF token string (read from
``Settings.hf_token_path``); this adapter never reads the filesystem for
secrets directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pdomain_ocr_trainer_spa.adapters.dataset_sources import DatasetCropRef, DatasetPageRef
    from pdomain_ocr_trainer_spa.core.enums import SplitEnum, TaskEnum
    from pdomain_ocr_trainer_spa.settings import Settings

# Map internal task names to HF split names (huggingface_hub snapshot paths).
_SPLIT_MAP: dict[str, str] = {
    "train": "train",
    "val": "validation",
    "test": "test",
}


class HuggingFaceDatasetSource:
    """HF dataset source — preview + fetch-to-local (spec 09 §3)."""

    name = "huggingface"

    def __init__(self, settings: Settings, *, token: str) -> None:
        self._settings = settings
        self._token = token

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    def list(
        self,
        profile: str,
        task: TaskEnum,
        split: SplitEnum,
    ) -> Iterator[DatasetPageRef | DatasetCropRef]:
        """Yield rows from the HF dataset (lazy streaming).

        Requires ``huggingface_hub`` + ``datasets`` at runtime.
        Not used by the SPA web process directly — the worker subprocess
        calls ``fetch_to_local`` and then reads from the materialized dir.
        """
        raise NotImplementedError(
            "list() is for worker subprocess use; the SPA web process uses fetch_to_local() instead."
        )

    def fetch_to_local(
        self,
        profile: str,
        task: TaskEnum,
        split: SplitEnum,
    ) -> Path:
        """Materialize an HF dataset snapshot into hf_cache_dir (spec 09 §3).

        Returns the path to the materialized recognition/detection dir.
        Requires ``huggingface_hub`` at runtime.
        """
        raise NotImplementedError(
            "fetch_to_local() is intended for worker subprocess use; "
            "the repo and revision must be supplied by the caller."
        )

    def fetch_repo_to_local(
        self,
        repo: str,
        revision: str,
        task: str,
    ) -> Path:
        """Snapshot an HF repo at ``revision`` into the local cache.

        Materializes the dataset into::

            <hf_cache_dir>/<repo_slug>@<revision>/<task>/

        Returns the path to the task subdirectory.  Uses
        ``huggingface_hub.snapshot_download`` so repeated calls are cheap
        (the HF cache deduplicates by repo + revision).
        """
        try:
            import huggingface_hub
        except ImportError as exc:
            raise RuntimeError(
                "huggingface_hub is not installed. Add it to the environment or use local sources only."
            ) from exc

        cache_dir = self._settings.hf_cache_dir or Path.home() / ".cache" / "huggingface"
        repo_slug = repo.replace("/", "--")
        target = cache_dir / f"{repo_slug}@{revision}" / task
        target.mkdir(parents=True, exist_ok=True)

        # snapshot_download caches by (repo_id, revision) — subsequent calls
        # return the cached path immediately.
        snapshot_dir = huggingface_hub.snapshot_download(
            repo_id=repo,
            revision=revision,
            token=self._token,
            repo_type="dataset",
            cache_dir=str(cache_dir / "hf_hub"),
        )

        # Materialize recognition shape: images/ + labels.json from metadata.jsonl
        snapshot_path = Path(snapshot_dir)
        self._materialize_task(snapshot_path, target, task)
        return target

    def _materialize_task(self, snapshot: Path, target: Path, task: str) -> None:
        """Copy/link files from the HF snapshot into the DocTR-compatible layout.

        Recognition layout: ``images/`` + ``labels.json``
        Detection layout:   ``images/`` + ``labels.json``

        The SPA follows the mapping table from spec 09 §3.
        """
        if task == "recognition":
            self._materialize_recognition(snapshot, target)
        elif task == "detection":
            self._materialize_detection(snapshot, target)
        # Other tasks (typeface, glyph) pass through as-is.

    def _materialize_recognition(self, snapshot: Path, target: Path) -> None:
        """Materialize recognition/v1 shape: imagefolder + metadata.jsonl → labels.json."""
        images_src = snapshot / "images"
        metadata_src = snapshot / "metadata.jsonl"
        images_dst = target / "images"
        images_dst.mkdir(exist_ok=True)

        # Hard-link images when possible; fall back to copy.
        if images_src.exists():
            for img in images_src.iterdir():
                dst = images_dst / img.name
                if not dst.exists():
                    try:
                        dst.hardlink_to(img)
                    except OSError:
                        import shutil

                        shutil.copy2(img, dst)

        # Build labels.json from metadata.jsonl
        labels: dict[str, str] = {}
        if metadata_src.exists():
            for raw_line in metadata_src.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    row: dict[str, Any] = json.loads(line)
                except ValueError:
                    continue
                file_name = row.get("file_name", "")
                text = row.get("text", "")
                if file_name and text:
                    labels[file_name] = text

        labels_dst = target / "labels.json"
        labels_dst.write_text(json.dumps(labels, ensure_ascii=False), encoding="utf-8")

    def _materialize_detection(self, snapshot: Path, target: Path) -> None:
        """Materialize detection/v1 shape: parquet → labels.json."""
        # Basic passthrough — detection parquet decoding is worker-side.
        # The SPA just ensures the snapshot directory is accessible.
        import shutil

        images_src = snapshot / "images"
        labels_src = snapshot / "labels.json"
        images_dst = target / "images"
        images_dst.mkdir(exist_ok=True)

        if images_src.exists():
            for img in images_src.iterdir():
                dst = images_dst / img.name
                if not dst.exists():
                    try:
                        dst.hardlink_to(img)
                    except OSError:
                        shutil.copy2(img, dst)

        if labels_src.exists() and not (target / "labels.json").exists():
            shutil.copy2(labels_src, target / "labels.json")

    # ------------------------------------------------------------------
    # Preview (spec 09 §7)
    # ------------------------------------------------------------------

    def preview(
        self,
        *,
        repo: str,
        revision: str,
        task: str,
        split: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return up to ``limit`` rows from the HF dataset for UI preview.

        Uses ``huggingface_hub.hf_hub_download`` to fetch only the
        metadata file, avoiding a full snapshot download for the preview.
        Falls back to an empty list on any network error so the UI can
        surface the error through the banner mechanism instead.
        """
        try:
            import huggingface_hub
        except ImportError:
            return []

        try:
            cache_dir = self._settings.hf_cache_dir or Path.home() / ".cache" / "huggingface"
            # Try to download just metadata.jsonl for recognition preview.
            metadata_path = huggingface_hub.hf_hub_download(
                repo_id=repo,
                filename="metadata.jsonl",
                revision=revision,
                token=self._token,
                repo_type="dataset",
                cache_dir=str(cache_dir / "hf_hub"),
            )
            rows: list[dict[str, Any]] = []
            for raw_line in Path(metadata_path).read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    row: dict[str, Any] = json.loads(line)
                    rows.append(row)
                except ValueError:
                    continue
                if len(rows) >= limit:
                    break
        except Exception:  # noqa: BLE001
            return []
        else:
            return rows
        return []
