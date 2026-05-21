"""RequestIdMiddleware + error-handler integration tests."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from pd_ocr_trainer_spa.core.errors import AppError, FieldError
from pd_ocr_trainer_spa.middleware.error_handler import app_error_handler
from pd_ocr_trainer_spa.middleware.request_id import REQUEST_ID_HEADER, RequestIdMiddleware


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    app.add_exception_handler(AppError, app_error_handler)

    @app.get("/ok")
    async def ok() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/boom")
    async def boom() -> None:
        raise AppError(
            "profile.has_data",
            "profile still has data",
            status_code=409,
            details=[FieldError(loc=["name"], msg="bad")],
        )

    return app


def test_request_id_echoed_on_response() -> None:
    resp = TestClient(_app()).get("/ok")
    assert REQUEST_ID_HEADER in resp.headers
    assert resp.headers[REQUEST_ID_HEADER]


def test_caller_supplied_request_id_is_honoured() -> None:
    resp = TestClient(_app()).get("/ok", headers={REQUEST_ID_HEADER: "caller-123"})
    assert resp.headers[REQUEST_ID_HEADER] == "caller-123"


def test_app_error_rendered_as_envelope() -> None:
    resp = TestClient(_app(), raise_server_exceptions=False).get("/boom")
    assert resp.status_code == 409
    body = resp.json()
    assert body["code"] == "profile.has_data"
    assert body["message"] == "profile still has data"
    assert body["request_id"] == resp.headers[REQUEST_ID_HEADER]
    assert body["details"] == [{"loc": ["name"], "msg": "bad"}]
