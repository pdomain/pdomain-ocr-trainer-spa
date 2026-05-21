#!/usr/bin/env bash
# install.sh — install pd-ocr-trainer-spa via uv tool install
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
    echo "Installing pd-ocr-trainer-spa from $1 ..."
    uv tool install "$1"
else
    echo "Installing pd-ocr-trainer-spa from pd-index ..."
    uv tool install \
        --index https://concavetrillion.github.io/pd-index \
        pd-ocr-trainer-spa
fi

echo ""
echo "✅ pd-ocr-trainer-spa installed."
echo "   Run: pd-ocr-trainer-ui --port 8081"
