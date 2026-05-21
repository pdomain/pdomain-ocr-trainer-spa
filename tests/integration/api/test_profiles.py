"""Integration tests for the /api/profiles routes (spec 04 §6)."""

from __future__ import annotations

import json
import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from pd_ocr_trainer_spa.settings import Settings


def test_scenario_1_fresh_install_lists_only_all(client: TestClient) -> None:
    resp = client.get("/api/profiles")
    assert resp.status_code == 200
    body = resp.json()
    assert [p["name"] for p in body["profiles"]] == ["all"]
    only = body["profiles"][0]
    assert only["is_base"] is True
    assert only["counts"]["recognition_train_crops"] == 0
    assert body["has_legacy_layout"] is False


def test_scenario_3_create_profile(client: TestClient, settings: Settings) -> None:
    resp = client.post(
        "/api/profiles",
        json={"name": "Clogaelach", "language": "ga", "typeface": "clogaelach"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "clogaelach"
    assert body["language"] == "ga"
    assert body["typeface"] == "clogaelach"

    for root in (settings.ml_training_dir, settings.ml_validation_dir):
        toml_path = root / "clogaelach" / "profile.toml"
        assert toml_path.exists()
        data = tomllib.loads(toml_path.read_text())
        assert data["language"] == "ga"
        assert data["typeface"] == "clogaelach"


def test_create_duplicate_returns_409(client: TestClient) -> None:
    client.post("/api/profiles", json={"name": "dup"})
    resp = client.post("/api/profiles", json={"name": "dup"})
    assert resp.status_code == 409
    assert resp.json()["code"] == "profile.exists"


def test_scenario_4_patch_clears_fields(client: TestClient, settings: Settings) -> None:
    client.post(
        "/api/profiles",
        json={"name": "clogaelach", "language": "ga", "typeface": "clogaelach"},
    )
    resp = client.patch("/api/profiles/clogaelach", json={"typeface": None})
    assert resp.status_code == 200
    assert resp.json()["typeface"] is None
    train = settings.ml_training_dir / "clogaelach" / "profile.toml"
    assert tomllib.loads(train.read_text()).get("language") == "ga"

    resp = client.patch("/api/profiles/clogaelach", json={"language": None})
    assert resp.status_code == 200
    assert not train.exists()
    assert not (settings.ml_validation_dir / "clogaelach" / "profile.toml").exists()


def test_get_unknown_profile_returns_404(client: TestClient) -> None:
    resp = client.get("/api/profiles/ghost")
    assert resp.status_code == 404
    assert resp.json()["code"] == "profile.not_found"


def test_scenario_6_delete_profile(client: TestClient, settings: Settings) -> None:
    client.post("/api/profiles", json={"name": "clogaelach"})
    resp = client.delete("/api/profiles/clogaelach")
    assert resp.status_code == 204
    assert not (settings.ml_training_dir / "clogaelach").exists()
    assert not (settings.ml_validation_dir / "clogaelach").exists()


def test_delete_all_profile_returns_409(client: TestClient) -> None:
    resp = client.delete("/api/profiles/all")
    assert resp.status_code == 409
    assert resp.json()["code"] == "profile.is_base"


def test_delete_profile_with_data_returns_409(client: TestClient, settings: Settings) -> None:
    client.post("/api/profiles", json={"name": "hasdata"})
    task = settings.ml_training_dir / "hasdata" / "recognition"
    task.mkdir(parents=True, exist_ok=True)
    (task / "labels.json").write_text(json.dumps({"a.png": "x"}))
    resp = client.delete("/api/profiles/hasdata")
    assert resp.status_code == 409
    assert resp.json()["code"] == "profile.has_data"


def test_migrate_legacy_endpoint(client: TestClient, settings: Settings) -> None:
    flat = settings.ml_training_dir / "detection"
    flat.mkdir(parents=True)
    (flat / "labels.json").write_text("{}")

    resp = client.post("/api/profiles/migrate-legacy")
    assert resp.status_code == 204
    assert (settings.ml_training_dir / "all" / "detection" / "labels.json").exists()


def test_profiles_route_not_shadowed_by_spa_catchall(client: TestClient) -> None:
    resp = client.get("/api/profiles")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
