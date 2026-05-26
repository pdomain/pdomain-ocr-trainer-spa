"""Entry point for pdomain-ocr-trainer-spa.

Usage:
    pd-ocr-trainer-ui [--host HOST] [--port PORT] [--no-browser] [--log-level LEVEL]
"""

from __future__ import annotations

import argparse


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
        default=8081,
        help="Port to listen on (default: 8081)",
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

    import uvicorn

    from pdomain_ocr_trainer_spa.bootstrap import build_app
    from pdomain_ocr_trainer_spa.settings import Settings

    settings = Settings(host=args.host, port=args.port, log_level=args.log_level)
    app = build_app(settings)

    if not args.no_browser:
        import threading
        import time
        import webbrowser

        def _open_browser() -> None:
            time.sleep(1.0)
            webbrowser.open(f"http://{args.host}:{args.port}/")

        threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level.lower(), reload=args.reload)


if __name__ == "__main__":
    main()
