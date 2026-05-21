"""S3-backed IStorage impl — deferred, not implemented yet.

This module imports clean; every method raises AdapterNotImplementedError on call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pd_ocr_trainer_spa.core.errors import AdapterNotImplementedError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class S3Storage:
    """Deferred S3 IStorage impl — constructs, but every method raises."""

    def write_bytes(self, scope_root: Path, key: str, data: bytes) -> None:
        """Deferred — raises AdapterNotImplementedError."""
        raise AdapterNotImplementedError("S3 storage")

    def read_bytes(self, scope_root: Path, key: str) -> bytes:
        """Deferred — raises AdapterNotImplementedError."""
        raise AdapterNotImplementedError("S3 storage")

    def exists(self, scope_root: Path, key: str) -> bool:
        """Deferred — raises AdapterNotImplementedError."""
        raise AdapterNotImplementedError("S3 storage")

    def delete(self, scope_root: Path, key: str) -> None:
        """Deferred — raises AdapterNotImplementedError."""
        raise AdapterNotImplementedError("S3 storage")

    def list(self, scope_root: Path, prefix: str) -> Iterator[str]:
        """Deferred — raises AdapterNotImplementedError."""
        raise AdapterNotImplementedError("S3 storage")
