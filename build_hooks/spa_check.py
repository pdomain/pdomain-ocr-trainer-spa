"""Build-time assertion: SPA bytes must be inside the wheel.

Runs as a hatch build hook. Fails the build if the static/index.html
and at least one assets/*.js + assets/*.css are missing from
src/pdomain_ocr_trainer_spa/static/.

Usage: configured automatically by hatchling (see pyproject.toml).
To run manually:
    python build_hooks/spa_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

STATIC_DIR = Path(__file__).parent.parent / "src" / "pdomain_ocr_trainer_spa" / "static"


def check() -> None:
    """Assert that the SPA bundle is present in the static directory."""
    index = STATIC_DIR / "index.html"
    if not index.exists():
        print(
            f"ERROR: {index} not found.\n"
            "Run `make frontend-build` before `make build`.",
            file=sys.stderr,
        )
        sys.exit(1)

    content = index.read_text(encoding="utf-8")
    if not content.strip():
        print(f"ERROR: {index} is empty.", file=sys.stderr)
        sys.exit(1)

    assets_dir = STATIC_DIR / "assets"
    js_files = list(assets_dir.glob("*.js")) if assets_dir.exists() else []
    css_files = list(assets_dir.glob("*.css")) if assets_dir.exists() else []

    if not js_files:
        print(
            f"ERROR: No assets/*.js found in {STATIC_DIR}.\n"
            "Run `make frontend-build` before `make build`.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not css_files:
        print(
            f"ERROR: No assets/*.css found in {STATIC_DIR}.\n"
            "Run `make frontend-build` before `make build`.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"✅ SPA bundle present: {index.name} + {len(js_files)} JS + {len(css_files)} CSS files."
    )


if __name__ == "__main__":
    check()
