"""IModelRegistry adapter tests: filesystem, fake, HF Hub AdapterNotImplementedError."""

from __future__ import annotations

import pytest

from pd_ocr_trainer_spa.adapters.model_registry import IModelRegistry
from pd_ocr_trainer_spa.adapters.model_registry.fake import FakeModelRegistry
from pd_ocr_trainer_spa.adapters.model_registry.filesystem import FilesystemModelRegistry
from pd_ocr_trainer_spa.adapters.model_registry.huggingface_hub import (
    HuggingFaceHubModelRegistry,
)
from pd_ocr_trainer_spa.core.errors import AdapterNotImplementedError
from pd_ocr_trainer_spa.core.models import ModelPaths, ModelSidecar


class _Run:
    def __init__(self, profile: str) -> None:
        self.profile = profile


def _sidecar(name: str = "pd-en-roman-detection-2026-05-21") -> ModelSidecar:
    return ModelSidecar(
        name=name,
        task="detection",
        language="en",
        typeface="roman",
        doctr_arch="db_resnet50",
    )


def test_filesystem_registry_satisfies_protocol(tmp_path) -> None:
    assert isinstance(FilesystemModelRegistry(tmp_path), IModelRegistry)


def test_filesystem_registry_empty_list(tmp_path) -> None:
    assert FilesystemModelRegistry(tmp_path).list() == []


def test_filesystem_registry_write_and_get(tmp_path) -> None:
    reg = FilesystemModelRegistry(tmp_path / "shared-models")
    weights = tmp_path / "src.pt"
    weights.write_bytes(b"fake-weights")
    sidecar = _sidecar()
    model = reg.write_artefacts(
        _Run("all"),
        ModelPaths(weights=str(weights), sidecar="ignored"),
        sidecar,
    )
    assert model.name == sidecar.name
    assert reg.get(sidecar.name) is not None
    assert [m.name for m in reg.list()] == [sidecar.name]


def test_filesystem_registry_get_missing_returns_none(tmp_path) -> None:
    assert FilesystemModelRegistry(tmp_path).get("nope") is None


def test_filesystem_registry_publish_raises(tmp_path) -> None:
    reg = FilesystemModelRegistry(tmp_path / "shared-models")
    weights = tmp_path / "src.pt"
    weights.write_bytes(b"w")
    model = reg.write_artefacts(_Run("all"), ModelPaths(weights=str(weights), sidecar="x"), _sidecar())
    with pytest.raises(AdapterNotImplementedError):
        reg.publish(model, "owner/repo", lambda _e: None)


def test_fake_registry_satisfies_protocol() -> None:
    assert isinstance(FakeModelRegistry(), IModelRegistry)


def test_fake_registry_write_get_list() -> None:
    reg = FakeModelRegistry()
    sidecar = _sidecar()
    model = reg.write_artefacts(_Run("all"), ModelPaths(weights="w", sidecar="s"), sidecar)
    assert reg.get(sidecar.name) == model
    assert reg.list() == [model]


def test_fake_registry_publish_records_publication() -> None:
    reg = FakeModelRegistry()
    model = reg.write_artefacts(_Run("all"), ModelPaths(weights="w", sidecar="s"), _sidecar())
    publication = reg.publish(model, "owner/repo", lambda _e: None)
    assert publication.repo == "owner/repo"
    refreshed = reg.get(model.name)
    assert refreshed is not None
    assert refreshed.published_to == [publication]


def test_hf_hub_registry_satisfies_protocol() -> None:
    assert isinstance(HuggingFaceHubModelRegistry(), IModelRegistry)


def test_hf_hub_registry_methods_raise_not_implemented() -> None:
    reg = HuggingFaceHubModelRegistry()
    with pytest.raises(AdapterNotImplementedError):
        reg.list()
    with pytest.raises(AdapterNotImplementedError):
        reg.get("x")
    with pytest.raises(AdapterNotImplementedError):
        reg.write_artefacts(_Run("all"), ModelPaths(weights="w", sidecar="s"), _sidecar())
