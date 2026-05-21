"""IStorage Protocol — the storage backend surface (spec 02-backend §4.1).

Keys are forward-slash-joined paths under a per-call scope root. The method
set is fixed by the spec; a future drift fails the Protocol shape-pin test.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@runtime_checkable
class IStorage(Protocol):
    """Profile-scoped object-store interface used for run / model artefact IO."""

    def write_bytes(self, scope_root: Path, key: str, data: bytes) -> None: ...

    def read_bytes(self, scope_root: Path, key: str) -> bytes: ...

    def exists(self, scope_root: Path, key: str) -> bool: ...

    def delete(self, scope_root: Path, key: str) -> None: ...

    def list(self, scope_root: Path, prefix: str) -> Iterator[str]: ...
