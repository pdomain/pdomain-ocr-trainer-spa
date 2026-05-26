"""Error codes, the AppError exception, and the ErrorEnvelope wire model (spec 02-backend §7)."""

from __future__ import annotations

from pydantic import BaseModel


class FieldError(BaseModel):
    """A single field-level validation error."""

    loc: list[str]
    msg: str


class ErrorEnvelope(BaseModel):
    """The JSON body returned for every non-2xx response."""

    code: str
    message: str
    details: list[FieldError] | None = None
    request_id: str


class AppError(Exception):
    """A domain error carrying a stable code and an HTTP status.

    The error_handler middleware renders this as an ErrorEnvelope. Raise
    AppError (not HTTPException) from domain code so the code string stays
    stable and the SPA can map it to a toast.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: list[FieldError] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class AdapterNotImplementedError(AppError):
    """Raised by deferred adapters (s3 storage, huggingface sources/registry).

    Importing the adapter module must always succeed; only calling a method
    raises this. Surfaced as HTTP 501.
    """

    def __init__(self, what: str) -> None:
        super().__init__(
            code="adapter.not_implemented",
            message=f"{what} is not implemented yet",
            status_code=501,
        )
