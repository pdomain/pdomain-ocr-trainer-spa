#!/usr/bin/env bash
# scripts/local-run.sh — run the SPA against the local-dev workspace.
#
# Deliberately does NOT delegate to `make run` — that path runs
# `frontend-build` → `frontend-install`, the registry path, which would
# discard the local-link overlay for @pdomain/pdomain-ui.
set -euo pipefail

# uv installs into UV_PROJECT_ENVIRONMENT when that is set and into .venv
# otherwise, so mirror the same rule instead of hardcoding either name. The
# pd-suite devcontainer sets ".venv-container" because the workspace is a bind
# mount shared with the host; a plain checkout outside a container gets .venv.
venv_under() {
  case "${UV_PROJECT_ENVIRONMENT:-}" in
    "") printf '%s/.venv' "$1" ;;
    /*) printf '%s' "$UV_PROJECT_ENVIRONMENT" ;;
    *) printf '%s/%s' "$1" "$UV_PROJECT_ENVIRONMENT" ;;
  esac
}

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GIT_COMMON_DIR="$(git -C "$REPO_ROOT" rev-parse --path-format=absolute --git-common-dir)"
CANONICAL_REPO_ROOT="$(dirname "$GIT_COMMON_DIR")"
PROJECT_VENV="$(venv_under "$CANONICAL_REPO_ROOT")"
MARKER="$PROJECT_VENV/.pdomain-local-mode"

if [[ ! -f "$MARKER" ]]; then
  echo "ERROR: not in local-dev mode. Run 'make local-dev' first." >&2
  exit 1
fi

make -C "$REPO_ROOT" local-setup-py
make -C "$REPO_ROOT" local-frontend-build

# --no-sync REQUIRED: plain `uv run` re-syncs and reverts the editable pdomain siblings.
exec uv run --no-sync --project "$CANONICAL_REPO_ROOT" python -m pdomain_ocr_trainer_spa ${ARGS:-}
