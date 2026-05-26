"""Integration tests for api/models.py — the model-registry REST surface (spec 08)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pdomain_ocr_trainer_spa.core.models import ModelSidecar

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from pdomain_ocr_trainer_spa.settings import Settings


def _write_model(
    settings: Settings,
    *,
    profile: str = "clogaelach",
    task: str = "recognition",
    name: str = "pd-ga-clogaelach-recognition-2026-05-05",
    sidecar: bool = True,
) -> str:
    leaf = settings.shared_models_dir / profile / task / name
    leaf.mkdir(parents=True, exist_ok=True)
    (leaf / "model.pt").write_bytes(b"\x00")
    if sidecar:
        (leaf / f"{name}.metadata.json").write_text(
            ModelSidecar(name=name, task=task, language="ga").model_dump_json()
        )
    return name


def test_list_models_empty(client: TestClient) -> None:
    """GET /api/models on a fresh registry returns an empty list."""
    r = client.get("/api/models")
    assert r.status_code == 200
    assert r.json()["models"] == []


def test_list_and_get_model(client: TestClient, settings: Settings) -> None:
    """A model written to disk is discovered by list + get."""
    name = _write_model(settings)
    listed = client.get("/api/models").json()["models"]
    assert [m["model"]["name"] for m in listed] == [name]
    assert listed[0]["has_sidecar"] is True

    one = client.get(f"/api/models/{name}")
    assert one.status_code == 200
    assert one.json()["model"]["name"] == name


def test_get_unknown_model_404(client: TestClient) -> None:
    """GET an unknown model name returns 404."""
    assert client.get("/api/models/nope").status_code == 404


def test_get_sidecar(client: TestClient, settings: Settings) -> None:
    """GET /api/models/{name}/sidecar returns the raw sidecar."""
    name = _write_model(settings)
    r = client.get(f"/api/models/{name}/sidecar")
    assert r.status_code == 200
    assert r.json()["name"] == name


def test_regenerate_sidecar(client: TestClient, settings: Settings) -> None:
    """A weights-only model shows has_sidecar False; regenerate fixes it."""
    name = _write_model(settings, sidecar=False)
    listed = client.get("/api/models").json()["models"]
    assert listed[0]["has_sidecar"] is False

    r = client.post(f"/api/models/{name}/regenerate-sidecar")
    assert r.status_code == 200
    assert r.json()["has_sidecar"] is True


def test_patch_model(client: TestClient, settings: Settings) -> None:
    """PATCH updates the sidecar's typeface."""
    name = _write_model(settings)
    r = client.patch(f"/api/models/{name}", json={"typeface": "clogaelach"})
    assert r.status_code == 200
    assert r.json()["model"]["sidecar"]["typeface"] == "clogaelach"


def test_rename_model(client: TestClient, settings: Settings) -> None:
    """POST rename relocates the model and reflects the new name."""
    name = _write_model(settings, name="pd-clogaelach-recognition-legacy")
    new = "pd-ga-clogaelach-recognition-2026-05-05"
    r = client.post(f"/api/models/{name}/rename", json={"new_name": new})
    assert r.status_code == 200
    assert r.json()["model"]["name"] == new
    assert client.get(f"/api/models/{name}").status_code == 404


def test_rename_rejects_invalid_name(client: TestClient, settings: Settings) -> None:
    """Rename to a free-form name is rejected with 422."""
    name = _write_model(settings)
    r = client.post(f"/api/models/{name}/rename", json={"new_name": "free-form"})
    assert r.status_code == 422


def test_delete_model(client: TestClient, settings: Settings) -> None:
    """DELETE removes the model leaf dir."""
    name = _write_model(settings)
    assert client.delete(f"/api/models/{name}").status_code == 204
    assert client.get(f"/api/models/{name}").status_code == 404


def test_scan_models(client: TestClient, settings: Settings) -> None:
    """POST /api/models/scan returns a fresh listing."""
    _write_model(settings)
    r = client.post("/api/models/scan")
    assert r.status_code == 200
    assert len(r.json()["models"]) == 1


def test_trained_run_sidecar_visible_in_models(
    client: TestClient, settings: Settings
) -> None:
    """Acceptance (spec 08 §9.1): a worker-written sidecar appears in /models.

    Simulates what worker/train.py does on a successful run — writes the
    sidecar under shared_models_dir — then asserts the API discovers it.
    """
    from pdomain_ocr_trainer_spa.worker.train import write_model_sidecar

    name = "pd-ga-clogaelach-recognition-2026-05-21"
    shared = settings.shared_models_dir / "clogaelach" / "recognition"
    write_model_sidecar(
        {"model_name": name, "task": "recognition"},
        {"shared_models_dir": str(shared), "name": name, "epochs": 3},
    )
    listed = client.get("/api/models").json()["models"]
    assert any(m["model"]["name"] == name for m in listed)
    assert json.loads(
        (shared / name / f"{name}.metadata.json").read_text()
    )["task"] == "recognition"
