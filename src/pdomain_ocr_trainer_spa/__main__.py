"""Entry point for pdomain-ocr-trainer-spa.

Usage:
    pdomain-ocr-trainer-ui [--host HOST] [--port PORT] [--no-browser] [--log-level LEVEL]

Port selection priority (highest to lowest):
    1. --port CLI flag
    2. PD_OCR_TRAINER_SPA_PORT env var
    3. DEFAULT_PORT (8081), with automatic fallback to the next free port

Port resolution, suite registration, and startup-URL printing are all
delegated to :func:`pdomain_ops.suite.bootstrap_spa`.
"""

from __future__ import annotations

import argparse

from pdomain_ops.suite import bootstrap_spa

DEFAULT_PORT: int = 8081


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

    preferred = args.port if args.port is not None else DEFAULT_PORT

    port = bootstrap_spa(
        preferred=preferred,
        caller_package="pdomain_ocr_trainer_spa",
        port_env="PD_OCR_TRAINER_SPA_PORT",
        host=args.host,
    )

    settings = Settings(host=args.host, port=port, log_level=args.log_level)
    app = build_app(settings)

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
