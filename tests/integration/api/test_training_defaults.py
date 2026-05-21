"""Integration tests for the /api/profiles/{name}/training-defaults routes (spec 04 §3.3)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_get_seed_detection(client: TestClient) -> None:
    resp = client.get("/api/profiles/all/training-defaults/detection/seed")
    assert resp.status_code == 200
    body = resp.json()
    assert body["task"] == "detection"
    assert body["args"]["arch"] == "db_resnet50"
    assert body["args"]["epochs"] == 100


def test_get_seed_recognition(client: TestClient) -> None:
    resp = client.get("/api/profiles/all/training-defaults/recognition/seed")
    assert resp.status_code == 200
    body = resp.json()
    assert body["task"] == "recognition"
    assert body["args"]["epochs"] == 10
    assert body["args"]["vocab_library"] == ["french"]


def test_get_unset_returns_404(client: TestClient) -> None:
    resp = client.get("/api/profiles/all/training-defaults/detection")
    assert resp.status_code == 404
    assert resp.json()["code"] == "training_defaults.not_set"


def test_put_then_get_round_trips_recognition(client: TestClient) -> None:
    seed = client.get(
        "/api/profiles/all/training-defaults/recognition/seed"
    ).json()["args"]
    seed["epochs"] = 50
    put = client.put("/api/profiles/all/training-defaults/recognition", json=seed)
    assert put.status_code == 200
    assert put.json()["args"]["epochs"] == 50

    got = client.get("/api/profiles/all/training-defaults/recognition")
    assert got.status_code == 200
    assert got.json()["args"]["epochs"] == 50


def test_put_then_get_round_trips_detection(client: TestClient) -> None:
    seed = client.get(
        "/api/profiles/all/training-defaults/detection/seed"
    ).json()["args"]
    seed["batch_size"] = 8
    put = client.put("/api/profiles/all/training-defaults/detection", json=seed)
    assert put.status_code == 200
    got = client.get("/api/profiles/all/training-defaults/detection")
    assert got.json()["args"]["batch_size"] == 8


def test_delete_falls_back_to_404(client: TestClient) -> None:
    client.put(
        "/api/profiles/all/training-defaults/detection", json={"epochs": 7}
    )
    resp = client.delete("/api/profiles/all/training-defaults/detection")
    assert resp.status_code == 204
    assert client.get("/api/profiles/all/training-defaults/detection").status_code == 404


def test_classifier_task_rejected_on_seed(client: TestClient) -> None:
    resp = client.get(
        "/api/profiles/all/training-defaults/glyph-classification/seed"
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "training_defaults.task_unsupported"
