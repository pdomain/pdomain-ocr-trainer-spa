from __future__ import annotations

import importlib
from importlib import metadata

import pytest

import pdomain_ocr_trainer_spa._version as version_module


def test_runtime_version_matches_installed_metadata() -> None:
    try:
        metadata_version = metadata.version("pdomain-ocr-trainer-spa")
    except metadata.PackageNotFoundError:
        assert version_module.__version__ == "0.0.0+unknown"
        return

    assert version_module.__version__ == metadata_version


def test_runtime_version_is_derived_from_package_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_version(package_name: str) -> str:
        assert package_name == "pdomain-ocr-trainer-spa"
        return "9.8.7+metadata"

    monkeypatch.setattr(metadata, "version", fake_version)

    try:
        reloaded_module = importlib.reload(version_module)
        assert reloaded_module.__version__ == "9.8.7+metadata"
    finally:
        monkeypatch.undo()
        importlib.reload(version_module)


def test_runtime_version_falls_back_when_package_metadata_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_version(package_name: str) -> str:
        assert package_name == "pdomain-ocr-trainer-spa"
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(metadata, "version", missing_version)

    try:
        reloaded_module = importlib.reload(version_module)
        assert reloaded_module.__version__ == "0.0.0+unknown"
    finally:
        monkeypatch.undo()
        importlib.reload(version_module)
