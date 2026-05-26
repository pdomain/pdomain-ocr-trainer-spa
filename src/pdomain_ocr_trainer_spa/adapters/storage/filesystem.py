"""Filesystem-backed IStorage impl with a path-traversal guard.

Keys with ``..`` segments or absolute-path tricks must not escape the
caller-supplied scope root, or a crafted key could read arbitrary host
files. The guard runs before any FS access.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


def _resolve(scope_root: Path, key: str) -> Path:
    """Resolve key against scope_root, raising ValueError on any escape attempt."""
    if key.startswith("/"):
        raise ValueError(f"key escapes scope root: {key!r} (absolute paths are not valid keys)")
    if any(part == ".." for part in Path(key).parts):
        raise ValueError(f"key escapes scope root: {key!r} (contains parent-dir reference)")
    candidate = (scope_root / key).resolve()
    root = scope_root.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"key escapes scope root: {key!r}")
    return candidate


class FilesystemStorage:
    """The v1 IStorage impl — direct reads/writes under a per-call scope root."""

    def write_bytes(self, scope_root: Path, key: str, data: bytes) -> None:
        """Write data at key under scope_root, creating parent dirs."""
        path = _resolve(scope_root, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read_bytes(self, scope_root: Path, key: str) -> bytes:
        """Read the bytes stored at key under scope_root."""
        return _resolve(scope_root, key).read_bytes()

    def exists(self, scope_root: Path, key: str) -> bool:
        """Return whether key exists under scope_root."""
        return _resolve(scope_root, key).exists()

    def delete(self, scope_root: Path, key: str) -> None:
        """Delete key under scope_root; a missing key is a no-op."""
        path = _resolve(scope_root, key)
        if path.exists():
            path.unlink()

    def list(self, scope_root: Path, prefix: str) -> Iterator[str]:
        """Yield scope-root-relative keys of every file under prefix."""
        base = _resolve(scope_root, prefix) if prefix else scope_root.resolve()
        root = scope_root.resolve()
        if not base.exists():
            return
        for entry in sorted(base.rglob("*")):
            if entry.is_file():
                yield entry.relative_to(root).as_posix()
