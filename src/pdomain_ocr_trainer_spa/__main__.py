"""Entry point for pdomain-ocr-trainer-spa.

Usage:
    pd-ocr-trainer-ui [--host HOST] [--port PORT] [--no-browser] [--log-level LEVEL]

Port selection priority (highest to lowest):
    1. --port CLI flag
    2. PD_OCR_TRAINER_SPA_PORT env var (read via Settings)
    3. DEFAULT_PORT (8081), with automatic fallback to the next free port
"""

from __future__ import annotations

import argparse
import os
import socket

DEFAULT_PORT: int = 8081


def _find_available_port_fallback(preferred: int, *, max_attempts: int = 50) -> int:
    """Stdlib fallback: walk upward from *preferred* until a free port is found."""
    for offset in range(max_attempts):
        candidate = preferred + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            try:
                sock.bind(("127.0.0.1", candidate))
            except OSError:
                continue
            else:
                return candidate
    return preferred  # give up — uvicorn will raise a clear error


def _find_available_port(preferred: int) -> int:
    """Return an available port, using pdomain-ops helper when present."""
    try:
        from pdomain_ops.suite import (
            find_available_port,  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]
        )

        return find_available_port(preferred)
    except (ImportError, AttributeError):
        return _find_available_port_fallback(preferred)


def _pick_port(preferred: int) -> int:
    """Probe *preferred* and return the first free port >= preferred."""
    return _find_available_port(preferred)


def _register_self_if_available(*, actual_port: int) -> None:
    """Call register_self with the actual bound port; silently skip if unavailable."""
    try:
        from pdomain_ops.suite import register_self

        register_self(
            _caller_package="pdomain_ocr_trainer_spa",
            actual_port=actual_port,
        )
    except Exception:  # noqa: BLE001, S110
        pass


def main() -> None:
    """Start the pdomain-ocr-trainer-spa server."""
    parser = argparse.ArgumentParser(
        description="pdomain-ocr-trainer-spa — FastAPI + React OCR model training UI",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to listen on (default: 8081, or PD_OCR_TRAINER_SPA_PORT env var)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the browser on startup",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level (default: INFO)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (dev mode)",
    )
    args = parser.parse_args()

    import uvicorn  # deferred to avoid slow import at module level

    from pdomain_ocr_trainer_spa.bootstrap import build_app
    from pdomain_ocr_trainer_spa.settings import Settings

    # Port priority: CLI flag > ENV var > DEFAULT_PORT
    if args.port is not None:
        preferred_port = args.port
    else:
        env_port = os.environ.get("PD_OCR_TRAINER_SPA_PORT")
        preferred_port = int(env_port) if env_port else DEFAULT_PORT

    port = _pick_port(preferred_port)

    _register_self_if_available(actual_port=port)

    settings = Settings(host=args.host, port=port, log_level=args.log_level)
    app = build_app(settings)

    print(f"pdomain-ocr-trainer-spa at http://{args.host}:{port}/")

    if not args.no_browser:
        import threading
        import time
        import webbrowser

        def _open_browser() -> None:
            time.sleep(1.0)
            webbrowser.open(f"http://{args.host}:{port}/")

        threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run(app, host=args.host, port=port, log_level=args.log_level.lower(), reload=args.reload)


if __name__ == "__main__":
    main()
