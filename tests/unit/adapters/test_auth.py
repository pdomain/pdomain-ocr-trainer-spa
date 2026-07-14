"""IAuth adapter tests: NoneAuth resolves every request to the local admin."""

from __future__ import annotations

from pdomain_ocr_trainer_spa.adapters.auth import AuthedUser, IAuth
from pdomain_ocr_trainer_spa.adapters.auth.none_ import NoneAuth


def test_none_auth_satisfies_protocol() -> None:
    assert isinstance(NoneAuth(), IAuth)


def test_none_auth_returns_local_admin() -> None:
    user = NoneAuth().current_user(request=object())  # type: ignore[arg-type]  # adapter deliberately ignores the request value
    assert user == AuthedUser(id="local", roles=["admin"])


def test_none_auth_ignores_request_content() -> None:
    """Even a bogus request resolves to the same fixed principal."""
    a = NoneAuth().current_user(request="bogus")  # type: ignore[arg-type]  # adapter deliberately ignores the request value
    b = NoneAuth().current_user(request=None)  # type: ignore[arg-type]  # adapter deliberately ignores the request value
    assert a == b
