"""Exception handlers that render errors as the ErrorEnvelope wire model (spec 02-backend §7)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

from pdomain_ocr_trainer_spa.core.errors import AppError, ErrorEnvelope

if TYPE_CHECKING:
    from starlette.requests import Request


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render an AppError as an ErrorEnvelope JSON body with its status code."""
    if not isinstance(exc, AppError):
        raise exc  # pragma: no cover — registered only for AppError
    envelope = ErrorEnvelope(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=exc.status_code, content=envelope.model_dump())
