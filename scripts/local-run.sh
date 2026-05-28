#!/usr/bin/env bash
# scripts/local-run.sh — run the SPA against the local-dev workspace.
#
# Deliberately does NOT delegate to `make run` — that path runs
# `frontend-build` → `frontend-install`, the registry path, which would
# discard the local-link overlay for @pdomain/pdomain-ui.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GIT_COMMON_DIR="$(git -C "$REPO_ROOT" rev-parse --path-format=absolute --git-common-dir)"
CANONICAL_REPO_ROOT="$(dirname "$GIT_COMMON_DIR")"
MARKER="$CANONICAL_REPO_ROOT/.venv/.pd-local-mode"

if [[ ! -f "$MARKER" ]]; then
  echo "ERROR: not in local-dev mode. Run 'make local-dev' first." >&2
  exit 1
fi

make -C "$REPO_ROOT" local-setup-py
make -C "$REPO_ROOT" local-frontend-build

# --no-sync REQUIRED: plain `uv run` re-syncs and reverts the editable pd-* siblings.
exec uv run --no-sync --project "$CANONICAL_REPO_ROOT" python -m pdomain_ocr_trainer_spa ${ARGS:-}
