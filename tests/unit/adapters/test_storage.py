"""IStorage adapter tests: FilesystemStorage, path-traversal guard, S3 AdapterNotImplementedError."""

from __future__ import annotations

import pytest

from pdomain_ocr_trainer_spa.adapters.storage import IStorage
from pdomain_ocr_trainer_spa.adapters.storage.filesystem import FilesystemStorage
from pdomain_ocr_trainer_spa.adapters.storage.s3 import S3Storage
from pdomain_ocr_trainer_spa.core.errors import AdapterNotImplementedError


def test_filesystem_storage_satisfies_protocol() -> None:
    assert isinstance(FilesystemStorage(), IStorage)


def test_write_read_round_trip(tmp_path) -> None:
    storage = FilesystemStorage()
    storage.write_bytes(tmp_path, "runs/a/manifest.json", b"hello")
    assert storage.exists(tmp_path, "runs/a/manifest.json")
    assert storage.read_bytes(tmp_path, "runs/a/manifest.json") == b"hello"


def test_delete_removes_key(tmp_path) -> None:
    storage = FilesystemStorage()
    storage.write_bytes(tmp_path, "x.txt", b"data")
    storage.delete(tmp_path, "x.txt")
    assert not storage.exists(tmp_path, "x.txt")


def test_delete_missing_key_is_noop(tmp_path) -> None:
    FilesystemStorage().delete(tmp_path, "never-existed.txt")


def test_list_returns_files_under_prefix(tmp_path) -> None:
    storage = FilesystemStorage()
    storage.write_bytes(tmp_path, "runs/a/one.txt", b"1")
    storage.write_bytes(tmp_path, "runs/a/two.txt", b"2")
    storage.write_bytes(tmp_path, "other/three.txt", b"3")
    assert sorted(storage.list(tmp_path, "runs")) == ["runs/a/one.txt", "runs/a/two.txt"]


def test_list_missing_prefix_is_empty(tmp_path) -> None:
    assert list(FilesystemStorage().list(tmp_path, "nope")) == []


@pytest.mark.parametrize(
    "bad_key",
    [
        "../escape.txt",
        "runs/../../etc/passwd",
        "/etc/passwd",
        "a/b/../../../outside.txt",
    ],
)
def test_path_traversal_guard_rejects_escape(tmp_path, bad_key: str) -> None:
    """Keys with .. segments or absolute paths must raise before any FS access."""
    storage = FilesystemStorage()
    with pytest.raises(ValueError, match="escapes scope root"):
        storage.write_bytes(tmp_path, bad_key, b"x")
    with pytest.raises(ValueError, match="escapes scope root"):
        storage.read_bytes(tmp_path, bad_key)
    with pytest.raises(ValueError, match="escapes scope root"):
        storage.exists(tmp_path, bad_key)


def test_path_traversal_guard_does_not_touch_fs(tmp_path) -> None:
    """A rejected key must not create or read anything on disk."""
    storage = FilesystemStorage()
    with pytest.raises(ValueError, match="escapes scope root"):
        storage.write_bytes(tmp_path, "../leaked.txt", b"x")
    assert not (tmp_path.parent / "leaked.txt").exists()


def test_s3_storage_satisfies_protocol() -> None:
    assert isinstance(S3Storage(), IStorage)


def test_s3_storage_methods_raise_not_implemented(tmp_path) -> None:
    storage = S3Storage()
    with pytest.raises(AdapterNotImplementedError):
        storage.write_bytes(tmp_path, "k", b"x")
    with pytest.raises(AdapterNotImplementedError):
        storage.read_bytes(tmp_path, "k")
    with pytest.raises(AdapterNotImplementedError):
        storage.exists(tmp_path, "k")
    with pytest.raises(AdapterNotImplementedError):
        storage.delete(tmp_path, "k")
    with pytest.raises(AdapterNotImplementedError):
        list(storage.list(tmp_path, "k"))
