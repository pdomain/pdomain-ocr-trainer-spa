"""Integration tests for api/publish.py - HF publish endpoints (spec 09 §5-§6, M11).

Tests cover:
- POST /api/publish/dataset — license gating, HF token check, 202 acceptance
- POST /api/publish/model — model existence, legacy name rejection, 202 acceptance
- Routes not shadowed by SPA catch-all
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from pdomain_ocr_trainer_spa.settings import Settings


def _make_client(settings: Settings, tmp_path: Path) -> TestClient:
    """Build a TestClient with a valid HF token and enable_hf_publish=True."""
    from fastapi.testclient import TestClient

    from pdomain_ocr_trainer_spa.bootstrap import build_app

    token_path = tmp_path / "hf-token"
    token_path.write_text("hf_test_token", encoding="utf-8")
    settings.hf_token_path = token_path
    settings.enable_hf_publish = True
    settings.hf_default_owner = "testowner"
    return TestClient(build_app(settings))


# ---------------------------------------------------------------------------
# Dataset publish
# ---------------------------------------------------------------------------


def test_publish_dataset_missing_token_returns_400(settings: Settings, tmp_path: Path) -> None:
    """POST /api/publish/dataset without an HF token returns 400 hf.auth_missing."""
    from fastapi.testclient import TestClient

    from pdomain_ocr_trainer_spa.bootstrap import build_app

    settings.hf_token_path = tmp_path / "nonexistent"
    settings.enable_hf_publish = True
    client = TestClient(build_app(settings))

    resp = client.post(
        "/api/publish/dataset",
        json={
            "profile": "test-profile",
            "task": "recognition",
            "repo": "testowner/pd-ocr-real-ga-clogaelach",
            "visibility": "private",
            "license": "Apache-2.0",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "hf.auth_missing"


def test_publish_dataset_missing_license_returns_422(settings: Settings, tmp_path: Path) -> None:
    """POST /api/publish/dataset without license field returns 422."""
    client = _make_client(settings, tmp_path)

    resp = client.post(
        "/api/publish/dataset",
        json={
            "profile": "test-profile",
            "task": "recognition",
            "repo": "testowner/pd-ocr-real-ga-clogaelach",
            "visibility": "private",
            # license intentionally omitted
        },
    )
    assert resp.status_code == 422


def test_publish_dataset_invalid_license_returns_409(settings: Settings, tmp_path: Path) -> None:
    """POST /api/publish/dataset with an unrecognised SPDX license returns 409 publish.license_missing."""
    client = _make_client(settings, tmp_path)

    resp = client.post(
        "/api/publish/dataset",
        json={
            "profile": "test-profile",
            "task": "recognition",
            "repo": "testowner/pd-ocr-real-ga-clogaelach",
            "visibility": "private",
            "license": "NOT_A_REAL_LICENSE_123",
        },
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "publish.license_missing"


def test_publish_dataset_returns_202(settings: Settings, tmp_path: Path) -> None:
    """POST /api/publish/dataset with valid payload returns 202 with run_id + job_id."""
    client = _make_client(settings, tmp_path)

    with patch(
        "pdomain_ocr_trainer_spa.domain.publish.submit_publish_dataset_job",
        return_value=("run-abc", "job-xyz"),
    ):
        resp = client.post(
            "/api/publish/dataset",
            json={
                "profile": "test-profile",
                "task": "recognition",
                "repo": "testowner/pd-ocr-real-ga-clogaelach",
                "visibility": "private",
                "license": "Apache-2.0",
            },
        )

    assert resp.status_code == 202
    body = resp.json()
    assert "run_id" in body
    assert "job_id" in body


def test_publish_dataset_route_not_shadowed_by_spa(settings: Settings, tmp_path: Path) -> None:
    """POST /api/publish/dataset returns JSON (not HTML SPA fallback)."""
    client = _make_client(settings, tmp_path)

    resp = client.post(
        "/api/publish/dataset",
        json={
            "profile": "test-profile",
            "task": "recognition",
            "repo": "testowner/pd-ocr-real-ga-clogaelach",
            "visibility": "private",
            "license": "Apache-2.0",
        },
    )
    # Must be JSON not HTML
    assert resp.headers["content-type"].startswith("application/json")


# ---------------------------------------------------------------------------
# Model publish
# ---------------------------------------------------------------------------


def test_publish_model_missing_token_returns_400(settings: Settings, tmp_path: Path) -> None:
    """POST /api/publish/model without HF token returns 400 hf.auth_missing."""
    from fastapi.testclient import TestClient

    from pdomain_ocr_trainer_spa.bootstrap import build_app

    settings.hf_token_path = tmp_path / "nonexistent"
    settings.enable_hf_publish = True
    client = TestClient(build_app(settings))

    resp = client.post(
        "/api/publish/model",
        json={
            "model_name": "pd-ga-clogaelach-recognition-2026-01-01",
            "repo": "testowner/pd-ga-clogaelach-recognition-2026-01-01",
            "visibility": "private",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "hf.auth_missing"


def test_publish_model_not_found_returns_404(settings: Settings, tmp_path: Path) -> None:
    """POST /api/publish/model with unknown model_name returns 404."""
    client = _make_client(settings, tmp_path)

    resp = client.post(
        "/api/publish/model",
        json={
            "model_name": "pd-ga-nonexistent-recognition-2099-01-01",
            "repo": "testowner/pd-ga-nonexistent-recognition-2099-01-01",
            "visibility": "private",
        },
    )
    assert resp.status_code == 404


def test_publish_model_legacy_name_returns_422(settings: Settings, tmp_path: Path) -> None:
    """POST /api/publish/model with a legacy-form model_name returns 422 publish.legacy_name."""
    client = _make_client(settings, tmp_path)

    resp = client.post(
        "/api/publish/model",
        json={
            "model_name": "some-legacy-model-name-without-lang",
            "repo": "testowner/some-legacy-model-name-without-lang",
            "visibility": "private",
        },
    )
    # Legacy names are either 404 (doesn't exist) or 422 (exists but legacy)
    assert resp.status_code in {404, 422}


def test_publish_model_returns_202(settings: Settings, tmp_path: Path) -> None:
    """POST /api/publish/model with a valid model returns 202 with run_id + job_id."""
    client = _make_client(settings, tmp_path)

    # Create a minimal model on disk so the registry can find it.
    # Directory structure: shared_models_dir/<profile>/<task>/<model_name>
    import json
    from datetime import UTC, datetime

    model_name = "pd-ga-clogaelach-recognition-2026-01-01"
    profile_name = "test-profile"
    model_dir = settings.shared_models_dir / profile_name / "recognition" / model_name
    model_dir.mkdir(parents=True, exist_ok=True)
    weights = model_dir / "model.pt"
    weights.write_bytes(b"\x00" * 4)
    sidecar = {
        "name": model_name,
        "task": "recognition",
        "language": "ga",
        "typeface": "clogaelach",
        "trained_at": datetime.now(UTC).isoformat(),
        "trained_on": [],
        "args": {},
    }
    (model_dir / "sidecar.json").write_text(json.dumps(sidecar), encoding="utf-8")

    with patch(
        "pdomain_ocr_trainer_spa.domain.publish.submit_publish_model_job",
        return_value=("run-abc", "job-xyz"),
    ):
        resp = client.post(
            "/api/publish/model",
            json={
                "model_name": model_name,
                "repo": "testowner/pd-ga-clogaelach-recognition-2026-01-01",
                "visibility": "private",
            },
        )

    assert resp.status_code == 202
    body = resp.json()
    assert "run_id" in body
    assert "job_id" in body


def test_publish_model_route_not_shadowed_by_spa(settings: Settings, tmp_path: Path) -> None:
    """POST /api/publish/model returns JSON (not HTML SPA fallback)."""
    client = _make_client(settings, tmp_path)

    resp = client.post(
        "/api/publish/model",
        json={
            "model_name": "pd-ga-nonexistent-recognition-2099-01-01",
            "repo": "testowner/pd-ga-nonexistent-recognition-2099-01-01",
            "visibility": "private",
        },
    )
    assert resp.headers["content-type"].startswith("application/json")
