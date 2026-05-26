"""IAuth Protocol + AuthedUser model (spec 02-backend §4.2)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel

if TYPE_CHECKING:
    from fastapi import Request


class AuthedUser(BaseModel):
    """The principal resolved for a request."""

    id: str
    roles: list[str]


@runtime_checkable
class IAuth(Protocol):
    """Auth backend interface; the only v1 impl is NoneAuth."""

    def current_user(self, request: Request) -> AuthedUser | None: ...
