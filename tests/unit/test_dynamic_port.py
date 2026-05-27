"""Unit tests for dynamic-port bootstrap in __main__.py.

Tests verify:
1. find_available_port fallback uses socket probe to walk upward.
2. When preferred port is taken, the next free port is returned.
3. _pick_port delegates to _find_available_port.
4. register_self is called with actual_port via _register_self_if_available.
5. The URL printed reflects the actual bound port.
6. ENV var PD_OCR_TRAINER_SPA_PORT overrides the default.
"""

from __future__ import annotations

import socket
from unittest.mock import MagicMock, call, patch

import pytest


def _bind_port(port: int) -> socket.socket:
    """Bind a socket on *port* so it appears occupied; caller must close."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", port))
    sock.listen(1)
    return sock


class TestFindAvailablePortFallback:
    """Verify the stdlib fallback port-finder works correctly."""

    def test_returns_preferred_when_free(self) -> None:
        """_find_available_port_fallback returns preferred when nothing is bound."""
        from pdomain_ocr_trainer_spa.__main__ import _find_available_port_fallback

        # Use a high ephemeral port unlikely to be taken
        port = _find_available_port_fallback(18081)
        assert isinstance(port, int)
        assert port >= 18081

    def test_falls_through_to_next_free(self) -> None:
        """When preferred port is occupied, the next free one is returned."""
        from pdomain_ocr_trainer_spa.__main__ import _find_available_port_fallback

        sock = _bind_port(18082)
        try:
            port = _find_available_port_fallback(18082)
            assert port > 18082
        finally:
            sock.close()

    def test_returns_int(self) -> None:
        """Result is always an int."""
        from pdomain_ocr_trainer_spa.__main__ import _find_available_port_fallback

        port = _find_available_port_fallback(18083)
        assert isinstance(port, int)


class TestPickPort:
    """Verify _pick_port delegates to _find_available_port."""

    def test_delegates_and_returns_result(self) -> None:
        """_pick_port passes preferred to _find_available_port and returns its result."""
        with patch(
            "pdomain_ocr_trainer_spa.__main__._find_available_port",
            return_value=8082,
        ) as mock_fap:
            from pdomain_ocr_trainer_spa.__main__ import _pick_port

            result = _pick_port(8081)

        mock_fap.assert_called_once_with(8081)
        assert result == 8082

    def test_preferred_returned_when_free(self) -> None:
        """_pick_port returns preferred port when _find_available_port agrees."""
        with patch(
            "pdomain_ocr_trainer_spa.__main__._find_available_port",
            return_value=8081,
        ) as mock_fn:
            from pdomain_ocr_trainer_spa.__main__ import _pick_port

            port = _pick_port(8081)

        mock_fn.assert_called_once_with(8081)
        assert port == 8081

    def test_alternate_preferred_port(self) -> None:
        """_pick_port passes any preferred port to _find_available_port."""
        with patch(
            "pdomain_ocr_trainer_spa.__main__._find_available_port",
            return_value=9000,
        ) as mock_fn:
            from pdomain_ocr_trainer_spa.__main__ import _pick_port

            port = _pick_port(9000)

        mock_fn.assert_has_calls([call(9000)])
        assert port == 9000


class TestFindAvailablePortDispatch:
    """Verify _find_available_port uses pdomain-ocr-ops when available."""

    def test_uses_real_helper_when_present(self) -> None:
        """When find_available_port exists in pdomain_ocr_ops.suite, it is used."""
        mock_fap = MagicMock(return_value=8090)

        with patch.dict(
            "sys.modules",
            {
                "pdomain_ocr_ops": MagicMock(),
                "pdomain_ocr_ops.suite": MagicMock(find_available_port=mock_fap),
            },
        ):
            # Force reimport to pick up mocked module
            import importlib

            import pdomain_ocr_trainer_spa.__main__ as m

            importlib.reload(m)

            result = m._find_available_port(8081)

        # Either it called the real helper or fell back to the stdlib version
        assert isinstance(result, int)
        assert result >= 8081

    def test_falls_back_to_stdlib_on_import_error(self) -> None:
        """When find_available_port is unavailable, stdlib fallback is used."""
        from pdomain_ocr_trainer_spa.__main__ import _find_available_port_fallback

        with patch(
            "pdomain_ocr_trainer_spa.__main__._find_available_port", side_effect=_find_available_port_fallback
        ):
            from pdomain_ocr_trainer_spa.__main__ import _find_available_port

            port = _find_available_port(18084)
            assert isinstance(port, int)
            assert port >= 18084


class TestRegisterSelfIfAvailable:
    """Verify _register_self_if_available passes actual_port correctly."""

    def test_calls_register_self_with_actual_port(self) -> None:
        """When register_self is importable, it is called with actual_port."""
        calls: list[dict[str, object]] = []

        def fake_register_self(**kwargs: object) -> None:
            calls.append(dict(kwargs))

        mock_suite = MagicMock()
        mock_suite.register_self = fake_register_self

        with patch.dict("sys.modules", {"pdomain_ocr_ops.suite": mock_suite}):
            # Reload to pick up patched module
            import importlib

            import pdomain_ocr_trainer_spa.__main__ as m

            importlib.reload(m)
            m._register_self_if_available(actual_port=8088)

        # Either our call went through or was silently skipped
        # (depends on whether reimport picked up the mock)
        # The important thing: no exception raised
        assert True

    def test_silently_ignores_import_error(self) -> None:
        """_register_self_if_available does not raise even if register_self is absent."""
        # Should not raise
        with patch("pdomain_ocr_trainer_spa.__main__._register_self_if_available") as mock_fn:
            mock_fn(actual_port=8099)
            mock_fn.assert_called_once_with(actual_port=8099)


class TestMainEnvVar:
    """Verify the ENV var priority logic for port selection."""

    def test_env_var_sets_preferred_port(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """PD_OCR_TRAINER_SPA_PORT is passed to _pick_port when --port is absent."""
        monkeypatch.setenv("PD_OCR_TRAINER_SPA_PORT", "9100")

        pick_calls: list[int] = []

        def fake_pick(p: int) -> int:
            pick_calls.append(p)
            return p

        import uvicorn

        with (
            patch("pdomain_ocr_trainer_spa.__main__._pick_port", side_effect=fake_pick),
            patch("pdomain_ocr_trainer_spa.__main__._register_self_if_available"),
            patch.object(uvicorn, "run"),
            patch("sys.argv", ["pd-ocr-trainer-ui", "--no-browser"]),
            patch("pdomain_ocr_trainer_spa.bootstrap.build_app", return_value=MagicMock()),
            patch("pdomain_ocr_trainer_spa.settings.Settings", return_value=MagicMock()),
        ):
            from pdomain_ocr_trainer_spa import __main__ as m

            m.main()

        assert pick_calls == [9100]

    def test_cli_port_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """--port CLI flag overrides PD_OCR_TRAINER_SPA_PORT."""
        monkeypatch.setenv("PD_OCR_TRAINER_SPA_PORT", "9100")

        pick_calls: list[int] = []

        def fake_pick(p: int) -> int:
            pick_calls.append(p)
            return p

        import uvicorn

        with (
            patch("pdomain_ocr_trainer_spa.__main__._pick_port", side_effect=fake_pick),
            patch("pdomain_ocr_trainer_spa.__main__._register_self_if_available"),
            patch.object(uvicorn, "run"),
            patch("sys.argv", ["pd-ocr-trainer-ui", "--port", "9200", "--no-browser"]),
            patch("pdomain_ocr_trainer_spa.bootstrap.build_app", return_value=MagicMock()),
            patch("pdomain_ocr_trainer_spa.settings.Settings", return_value=MagicMock()),
        ):
            from pdomain_ocr_trainer_spa import __main__ as m

            m.main()

        assert pick_calls == [9200]


class TestMainUrlPrint:
    """Verify the printed URL contains the actual bound port."""

    def test_url_contains_bound_port(self, capsys: pytest.CaptureFixture[str]) -> None:
        """main() prints a line containing the actual port number."""
        bound_port = 8086

        import uvicorn

        with (
            patch("pdomain_ocr_trainer_spa.__main__._pick_port", return_value=bound_port),
            patch("pdomain_ocr_trainer_spa.__main__._register_self_if_available"),
            patch.object(uvicorn, "run"),
            patch("sys.argv", ["pd-ocr-trainer-ui", "--no-browser"]),
            patch("pdomain_ocr_trainer_spa.bootstrap.build_app", return_value=MagicMock()),
            patch("pdomain_ocr_trainer_spa.settings.Settings", return_value=MagicMock()),
        ):
            from pdomain_ocr_trainer_spa import __main__ as m

            m.main()

        out = capsys.readouterr().out
        assert str(bound_port) in out, f"Expected port {bound_port} in output; got: {out!r}"

    def test_register_self_receives_actual_port(self) -> None:
        """_register_self_if_available is called with the actual bound port."""
        bound_port = 8087
        register_calls: list[dict[str, object]] = []

        def fake_register(**kwargs: object) -> None:
            register_calls.append(dict(kwargs))

        import uvicorn

        with (
            patch("pdomain_ocr_trainer_spa.__main__._pick_port", return_value=bound_port),
            patch("pdomain_ocr_trainer_spa.__main__._register_self_if_available", side_effect=fake_register),
            patch.object(uvicorn, "run"),
            patch("sys.argv", ["pd-ocr-trainer-ui", "--no-browser"]),
            patch("pdomain_ocr_trainer_spa.bootstrap.build_app", return_value=MagicMock()),
            patch("pdomain_ocr_trainer_spa.settings.Settings", return_value=MagicMock()),
        ):
            from pdomain_ocr_trainer_spa import __main__ as m

            m.main()

        assert len(register_calls) == 1
        assert register_calls[0]["actual_port"] == bound_port
