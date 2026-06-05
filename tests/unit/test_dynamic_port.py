"""Unit tests for dynamic-port bootstrap in __main__.py.

Since port resolution, registration, and URL printing are now delegated
to ``pdomain_ops.suite.bootstrap_spa``, tests mock that single entry
point and verify:

1. ``bootstrap_spa`` is called with the correct keyword args.
2. The ``--port`` CLI flag is passed as ``preferred``.
3. ``PD_OCR_TRAINER_SPA_PORT`` env var path: port_env is forwarded (bootstrap_spa owns it).
4. ``--port`` CLI flag overrides the env var path (preferred is set from args.port).
5. The returned port is passed to ``uvicorn.run`` and to ``Settings``.
6. The printed startup URL (from bootstrap_spa) contains the bound port.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_main(
    argv: list[str],
    bound_port: int = 8081,
) -> tuple[MagicMock, MagicMock]:
    """Invoke main() with *argv* and return (bootstrap_spa_mock, uvicorn_mock)."""
    import uvicorn

    bootstrap_mock = MagicMock(return_value=bound_port)
    uvicorn_mock = MagicMock()

    with (
        patch("pdomain_ocr_trainer_spa.__main__.bootstrap_spa", bootstrap_mock),
        patch.object(uvicorn, "run", uvicorn_mock),
        patch("sys.argv", argv),
        patch("pdomain_ocr_trainer_spa.bootstrap.build_app", return_value=MagicMock()),
        patch("pdomain_ocr_trainer_spa.settings.Settings", return_value=MagicMock()),
    ):
        from pdomain_ocr_trainer_spa import __main__ as m

        m.main()

    return bootstrap_mock, uvicorn_mock


# ---------------------------------------------------------------------------
# bootstrap_spa call args
# ---------------------------------------------------------------------------


class TestBootstrapSpaArgs:
    """Verify bootstrap_spa is called with the expected keyword arguments."""

    def test_default_preferred_port(self) -> None:
        """With no --port flag, preferred=DEFAULT_PORT (8081)."""
        bootstrap_mock, _ = _run_main(["pdomain-ocr-trainer-ui", "--no-browser"])

        bootstrap_mock.assert_called_once()
        _, kwargs = bootstrap_mock.call_args
        assert kwargs["preferred"] == 8081

    def test_cli_port_sets_preferred(self) -> None:
        """--port 9200 passes preferred=9200 to bootstrap_spa."""
        bootstrap_mock, _ = _run_main(["pdomain-ocr-trainer-ui", "--port", "9200", "--no-browser"])

        _, kwargs = bootstrap_mock.call_args
        assert kwargs["preferred"] == 9200

    def test_caller_package(self) -> None:
        """caller_package is always 'pdomain_ocr_trainer_spa'."""
        bootstrap_mock, _ = _run_main(["pdomain-ocr-trainer-ui", "--no-browser"])

        _, kwargs = bootstrap_mock.call_args
        assert kwargs["caller_package"] == "pdomain_ocr_trainer_spa"

    def test_port_env_forwarded(self) -> None:
        """port_env='PD_OCR_TRAINER_SPA_PORT' is forwarded to bootstrap_spa."""
        bootstrap_mock, _ = _run_main(["pdomain-ocr-trainer-ui", "--no-browser"])

        _, kwargs = bootstrap_mock.call_args
        assert kwargs["port_env"] == "PD_OCR_TRAINER_SPA_PORT"

    def test_host_forwarded(self) -> None:
        """--host is forwarded to bootstrap_spa."""
        bootstrap_mock, _ = _run_main(["pdomain-ocr-trainer-ui", "--host", "0.0.0.0", "--no-browser"])

        _, kwargs = bootstrap_mock.call_args
        assert kwargs["host"] == "0.0.0.0"

    def test_default_host(self) -> None:
        """Default host is 127.0.0.1."""
        bootstrap_mock, _ = _run_main(["pdomain-ocr-trainer-ui", "--no-browser"])

        _, kwargs = bootstrap_mock.call_args
        assert kwargs["host"] == "127.0.0.1"


# ---------------------------------------------------------------------------
# Port propagation
# ---------------------------------------------------------------------------


class TestPortPropagation:
    """Verify the bound port from bootstrap_spa flows to uvicorn and Settings."""

    def test_bound_port_passed_to_uvicorn(self) -> None:
        """uvicorn.run receives the port returned by bootstrap_spa."""
        bound = 9055
        _, uvicorn_mock = _run_main(["pdomain-ocr-trainer-ui", "--no-browser"], bound_port=bound)

        _, kwargs = uvicorn_mock.call_args
        assert kwargs["port"] == bound

    def test_bound_port_passed_to_settings(self) -> None:
        """Settings is constructed with the port returned by bootstrap_spa."""
        import uvicorn

        bound = 9056
        settings_cls = MagicMock(return_value=MagicMock())

        with (
            patch("pdomain_ocr_trainer_spa.__main__.bootstrap_spa", return_value=bound),
            patch.object(uvicorn, "run"),
            patch("sys.argv", ["pdomain-ocr-trainer-ui", "--no-browser"]),
            patch("pdomain_ocr_trainer_spa.bootstrap.build_app", return_value=MagicMock()),
            patch("pdomain_ocr_trainer_spa.settings.Settings", settings_cls),
        ):
            from pdomain_ocr_trainer_spa import __main__ as m

            m.main()

        _, kwargs = settings_cls.call_args
        assert kwargs["port"] == bound


# ---------------------------------------------------------------------------
# CLI flag behaviour
# ---------------------------------------------------------------------------


class TestCliFlagBehaviour:
    """Verify CLI flag semantics passed through to bootstrap_spa."""

    def test_cli_port_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When --port is given, preferred=CLI value regardless of env var."""
        monkeypatch.setenv("PD_OCR_TRAINER_SPA_PORT", "9100")

        bootstrap_mock, _ = _run_main(
            ["pdomain-ocr-trainer-ui", "--port", "9200", "--no-browser"],
        )

        _, kwargs = bootstrap_mock.call_args
        # preferred comes from --port; bootstrap_spa reads the env var internally
        assert kwargs["preferred"] == 9200

    def test_env_var_path_uses_default_preferred(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When only env var is set (no --port), preferred=DEFAULT_PORT; bootstrap_spa owns env resolution."""
        monkeypatch.setenv("PD_OCR_TRAINER_SPA_PORT", "9100")

        bootstrap_mock, _ = _run_main(["pdomain-ocr-trainer-ui", "--no-browser"])

        _, kwargs = bootstrap_mock.call_args
        assert kwargs["preferred"] == 8081  # DEFAULT_PORT
        assert kwargs["port_env"] == "PD_OCR_TRAINER_SPA_PORT"
