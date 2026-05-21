"""No-auth adapter — every request resolves to a fixed local admin user."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pd_ocr_trainer_spa.adapters.auth import AuthedUser

if TYPE_CHECKING:
    from fastapi import Request


class NoneAuth:
    """The v1 anonymous-everyone adapter — always returns the local admin."""

    def current_user(self, request: Request) -> AuthedUser | None:
        """Return the fixed local admin principal for any request."""
        del request  # unused — every caller is the local admin
        return AuthedUser(id="local", roles=["admin"])
