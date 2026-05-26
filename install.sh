#!/usr/bin/env bash
# install.sh — install pdomain-ocr-trainer-spa via uv tool install
#
# Usage:
#   ./install.sh              # install from pd-index PEP 503 registry (when available)
#   ./install.sh ./dist/*.whl  # install from a local wheel

set -euo pipefail

if ! command -v uv &>/dev/null; then
    echo "uv not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

if [[ $# -gt 0 ]]; then
    echo "Installing pdomain-ocr-trainer-spa from $1 ..."
    uv tool install "$1"
else
    echo "Installing pdomain-ocr-trainer-spa from pd-index ..."
    uv tool install \
        --index https://pdomain.github.io/pdomain-index-pip \
        pdomain-ocr-trainer-spa
fi

echo ""
echo "✅ pdomain-ocr-trainer-spa installed."
echo "   Run: pd-ocr-trainer-ui --port 8081"
