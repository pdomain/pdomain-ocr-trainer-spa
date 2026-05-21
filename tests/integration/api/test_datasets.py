"""Integration tests for the /api/profiles/.../datasets routes (spec 05 §11)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from pd_ocr_trainer_spa.bootstrap import build_app
from pd_ocr_trainer_spa.settings import Settings

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def export_root(tmp_path: Path) -> Path:
    """A labeler DocTR export root directory."""
    root = tmp_path / "doctr-export"
    root.mkdir()
    return root


@pytest.fixture
def kanban_settings(settings: Settings, export_root: Path) -> Settings:
    """Settings with the labeler export root wired in."""
    return settings.model_copy(update={"labeler_export_root": export_root})


@pytest.fixture
def kanban_client(kanban_settings: Settings) -> TestClient:
    """A TestClient whose app sees the export root."""
    return TestClient(build_app(kanban_settings))


def _seed_export(export_root: Path, project_id: str, labels: dict[str, str]) -> None:
    recog = export_root / project_id / "all" / "recognition"
    images = recog / "images"
    images.mkdir(parents=True)
    (recog / "labels.json").write_text(json.dumps(labels), encoding="utf-8")
    for crop in labels:
        (images / crop).write_bytes(b"png")


def test_get_kanban_empty(kanban_client: TestClient) -> None:
    resp = kanban_client.get("/api/profiles/all/datasets/recognition/kanban")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["columns"]) == {"unassigned", "train", "val"}
    assert body["task"] == "recognition"


def test_scenario_1_2_3_export_to_unassigned_then_apply(
    kanban_client: TestClient, kanban_settings: Settings, export_root: Path
) -> None:
    # 1. Drop an export — appears in unassigned.
    _seed_export(export_root, "myproj", {"myproj_1_0.png": "hello"})
    resp = kanban_client.get("/api/profiles/all/datasets/recognition/kanban")
    rows = resp.json()["columns"]["unassigned"]["rows"]
    assert [r["project_id"] for r in rows] == ["myproj"]
    chip_key = rows[0]["pages"][0]["key"]

    # 3. Apply stages it into train.
    resp = kanban_client.post(
        "/api/profiles/all/datasets/recognition/apply",
        json={"assignments": [{"key": chip_key, "target_split": "train"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [r["project_id"] for r in body["columns"]["train"]["rows"]] == ["myproj"]
    assert "X-Apply-Errors" not in resp.headers
    train_labels = (
        kanban_settings.ml_training_dir / "all" / "recognition" / "labels.json"
    )
    assert json.loads(train_labels.read_text()) == {"myproj_1_0.png": "hello"}


def test_scan_endpoint_returns_committed_truth(kanban_client: TestClient) -> None:
    resp = kanban_client.post("/api/profiles/all/datasets/recognition/scan")
    assert resp.status_code == 200
    assert set(resp.json()["columns"]) == {"unassigned", "train", "val"}


def test_include_toggles_round_trip(
    kanban_client: TestClient, kanban_settings: Settings
) -> None:
    resp = kanban_client.post(
        "/api/profiles/all/datasets/recognition/include-toggles",
        json={"include_detection": False, "include_recognition": True},
    )
    assert resp.status_code == 200
    assert resp.json()["include_detection"] is False
    state = kanban_settings.app_data_root / "profiles" / "all" / "kanban_state.json"
    assert json.loads(state.read_text())["include_detection"] is False


def test_apply_partial_failure_sets_header(
    kanban_client: TestClient, export_root: Path
) -> None:
    _seed_export(export_root, "good", {"good_1_0.png": "ok"})
    resp = kanban_client.post(
        "/api/profiles/all/datasets/recognition/apply",
        json={
            "assignments": [
                {"key": "good:good_1_0.png", "target_split": "train"},
                {"key": "ghost:ghost_9.png", "target_split": "train"},
            ]
        },
    )
    assert resp.status_code == 200
    errors = json.loads(resp.headers["X-Apply-Errors"])
    assert [e["key"] for e in errors] == ["ghost:ghost_9.png"]


def test_apply_total_failure_returns_409(kanban_client: TestClient) -> None:
    resp = kanban_client.post(
        "/api/profiles/all/datasets/recognition/apply",
        json={"assignments": [{"key": "ghost:ghost_9.png", "target_split": "train"}]},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "dataset.apply_failed"


def test_classifier_task_returns_501(kanban_client: TestClient) -> None:
    resp = kanban_client.get(
        "/api/profiles/all/datasets/typeface-classification/kanban"
    )
    assert resp.status_code == 501
    assert resp.json()["code"] == "dataset.task_unsupported"


def _seed_detection_export(
    export_root: Path, project_id: str, labels: dict[str, dict[str, object]]
) -> None:
    """Drop a labeler DocTR detection export under the export root."""
    det = export_root / project_id / "all" / "detection"
    images = det / "images"
    images.mkdir(parents=True)
    (det / "labels.json").write_text(json.dumps(labels), encoding="utf-8")
    for page in labels:
        (images / page).write_bytes(b"png")


def _det_meta(n_boxes: int) -> dict[str, object]:
    """A DocTR DetectionDataset labels.json value with ``n_boxes`` polygons."""
    return {
        "img_dimensions": [100, 100],
        "polygons": [[[0, 0], [1, 0], [1, 1], [0, 1]] for _ in range(n_boxes)],
    }


def test_detection_kanban_moves_pages_and_apply_writes_labels(
    kanban_client: TestClient, kanban_settings: Settings, export_root: Path
) -> None:
    meta = _det_meta(3)
    _seed_detection_export(export_root, "myproj", {"myproj_1.png": meta})

    # Detection export appears in the unassigned column as a page chip.
    resp = kanban_client.get("/api/profiles/all/datasets/detection/kanban")
    assert resp.status_code == 200
    rows = resp.json()["columns"]["unassigned"]["rows"]
    chip = rows[0]["pages"][0]
    assert chip["crop_name"] is None
    assert chip["label_text"] == "3 bboxes"

    # Apply moves the page into train and writes a valid detection labels.json.
    resp = kanban_client.post(
        "/api/profiles/all/datasets/detection/apply",
        json={"assignments": [{"key": chip["key"], "target_split": "train"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [r["project_id"] for r in body["columns"]["train"]["rows"]] == ["myproj"]
    train_labels = (
        kanban_settings.ml_training_dir / "all" / "detection" / "labels.json"
    )
    assert json.loads(train_labels.read_text()) == {"myproj_1.png": meta}


def test_detection_apply_moves_train_to_val(
    kanban_client: TestClient, kanban_settings: Settings
) -> None:
    meta = _det_meta(2)
    det = kanban_settings.ml_training_dir / "all" / "detection"
    (det / "images").mkdir(parents=True)
    (det / "labels.json").write_text(json.dumps({"p_1.png": meta}), encoding="utf-8")
    (det / "images" / "p_1.png").write_bytes(b"png")

    resp = kanban_client.post(
        "/api/profiles/all/datasets/detection/apply",
        json={"assignments": [{"key": "p:p_1.png", "target_split": "val"}]},
    )
    assert resp.status_code == 200
    val_labels = (
        kanban_settings.ml_validation_dir / "all" / "detection" / "labels.json"
    )
    assert json.loads(val_labels.read_text()) == {"p_1.png": meta}


def test_api_routes_not_shadowed_by_spa_catchall(kanban_client: TestClient) -> None:
    resp = kanban_client.get("/api/profiles/all/datasets/recognition/kanban")
    assert resp.headers["content-type"].startswith("application/json")
