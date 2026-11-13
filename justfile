set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
set positional-arguments

# Copy this wrapper and install-hooks with the shell setting to sibling justfiles.
[private]
_ai +args:
    #!/usr/bin/env bash
    set -euo pipefail
    if env AI= just --quiet "$@" > .ci-ai.log 2>&1; then
        printf 'PASS: %s\n' "$*"
    else
        result=$?
        printf 'FAIL: %s (exit %s)\n' "$*" "$result"
        if [[ -f scripts/ai_filter_log.py ]]; then
            uv run python scripts/ai_filter_log.py .ci-ai.log
        else
            tail -50 .ci-ai.log
        fi
        exit "$result"
    fi

install-hooks:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai install-hooks; fi
    if [[ -f .git ]]; then
        echo "hooks: worktree checkout - the canonical repo owns them, skipping"
    elif [[ -n "$(git config --get core.hooksPath || true)" ]]; then
        echo "hooks: core.hooksPath is set - leaving it alone, skipping"
    else
        uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
    fi

[private]
_pnpm +args:
    #!/usr/bin/env bash
    set -euo pipefail
    printf 'pnpm (%s):' "$PWD"
    printf ' %q' "$@"
    printf '\n'
    mise="$(command -v mise || printf '%s/.local/bin/mise' "$HOME")"
    if [[ -x "$mise" ]]; then
        exec "$mise" exec -- pnpm "$@"
    elif command -v pnpm >/dev/null 2>&1; then
        exec pnpm "$@"
    else
        echo "No pnpm/mise available. Run 'just mise-setup' or install Node." >&2
        exit 1
    fi

help:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai help; fi
    just --list

mise-trust-worktrees:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai mise-trust-worktrees; fi
    echo "🔐 Trusting mise config roots for this repo and generated worktrees..."
    mkdir -p "$HOME/.config/mise/conf.d"
    printf '%s\n' \
        '[settings]' \
        'trusted_config_paths = [' \
        '    "'"$(cd .. && pwd)"'",' \
        '    "/srv/bot-workspaces",' \
        ']' \
        > "$HOME/.config/mise/conf.d/ocr-container-worktrees.toml"
    echo "✅ mise trust roots configured."

mise-setup:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai mise-setup; fi
    just --quiet _task-mise-setup

[private]
_task-mise-setup: mise-trust-worktrees
    #!/usr/bin/env bash
    set -euo pipefail
    "$(command -v mise || printf '%s/.local/bin/mise' "$HOME")" install

setup:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai setup; fi
    uv sync --locked --group dev
    just --quiet install-hooks

update-hooks:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai update-hooks; fi
    uv run pre-commit autoupdate --freeze

install:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai install; fi
    just --quiet _task-install

[private]
_task-install: setup

uninstall:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai uninstall; fi
    uv tool uninstall pdomain-ocr-trainer-spa || true
    echo "✅ pdomain-ocr-trainer-spa uninstalled."

remove-venv:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai remove-venv; fi
    rm -rf "${UV_PROJECT_ENVIRONMENT:-.venv}"

reset:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai reset; fi
    just --quiet _task-reset

[private]
_task-reset: clean remove-venv setup
    #!/usr/bin/env bash
    set -euo pipefail
    echo "✅ Environment Reset!"

upgrade-deps:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai upgrade-deps; fi
    for marker in "${UV_PROJECT_ENVIRONMENT:-.venv}/.pdomain-local-mode" "${UV_PROJECT_ENVIRONMENT:-.venv}/.pdomain-dev-local"; do
        if [[ -f "$marker" ]]; then
            echo "Refusing dependency upgrades while $marker exists" >&2
            exit 1
        fi
    done
    echo "⬆️ Upgrading dependency lockfile..."
    uv lock --upgrade
    echo "📦 Syncing upgraded dependencies..."
    uv sync --group dev
    echo "✅ Dependencies upgraded and environment synced!"

lint:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai lint; fi
    uv run ruff check --select I --fix
    uv run ruff check --fix

format:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai format; fi
    uv run ruff format

format-check:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai format-check; fi
    uv run ruff format --check

typecheck:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai typecheck; fi
    uv run basedpyright src/pdomain_ocr_trainer_spa --level error

pre-commit-check:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai pre-commit-check; fi
    uv run pre-commit run --all-files

test:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai test; fi
    # Isolate shared-path discovery from the owner's suite registry.
    suite_data="$(mktemp -d)"
    trap 'rm -rf "$suite_data"' EXIT
    PD_SUITE_DATA_DIR="$suite_data" uv run pytest tests/ -v -n auto --ignore=tests/e2e

test-slow:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai test-slow; fi
    uv run pytest tests/ -v -m slow

frontend-install:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai frontend-install; fi
    cd frontend
    CI=true just --quiet --working-directory . --justfile ../justfile _pnpm install --frozen-lockfile

frontend-typecheck:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai frontend-typecheck; fi
    just --quiet _task-frontend-typecheck

[private]
_task-frontend-typecheck: frontend-install
    #!/usr/bin/env bash
    set -euo pipefail
    cd frontend
    just --quiet --working-directory . --justfile ../justfile _pnpm run typecheck

frontend-test:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai frontend-test; fi
    just --quiet _task-frontend-test

[private]
_task-frontend-test: frontend-install
    #!/usr/bin/env bash
    set -euo pipefail
    cd frontend
    just --quiet --working-directory . --justfile ../justfile _pnpm run test

frontend-build:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai frontend-build; fi
    just --quiet _task-frontend-build

[private]
_task-frontend-build: frontend-install
    #!/usr/bin/env bash
    set -euo pipefail
    cd frontend
    just --quiet --working-directory . --justfile ../justfile _pnpm run build

frontend-lint:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai frontend-lint; fi
    just --quiet _task-frontend-lint

[private]
_task-frontend-lint: frontend-install
    #!/usr/bin/env bash
    set -euo pipefail
    cd frontend
    just --quiet --working-directory . --justfile ../justfile _pnpm exec eslint . --fix

frontend-format:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai frontend-format; fi
    just --quiet _task-frontend-format

[private]
_task-frontend-format: frontend-install
    #!/usr/bin/env bash
    set -euo pipefail
    cd frontend
    just --quiet --working-directory . --justfile ../justfile _pnpm run format

frontend-format-check:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai frontend-format-check; fi
    just --quiet _task-frontend-format-check

[private]
_task-frontend-format-check: frontend-install
    #!/usr/bin/env bash
    set -euo pipefail
    cd frontend
    just --quiet --working-directory . --justfile ../justfile _pnpm run format:check

frontend-knip:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai frontend-knip; fi
    just --quiet _task-frontend-knip

[private]
_task-frontend-knip: frontend-install
    #!/usr/bin/env bash
    set -euo pipefail
    cd frontend
    just --quiet --working-directory . --justfile ../justfile _pnpm run knip

build:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai build; fi
    just --quiet frontend-build
    uv build --sdist
    uv build --wheel

[private]
_task-build: _task-frontend-build
    #!/usr/bin/env bash
    set -euo pipefail
    uv build --sdist
    uv build --wheel

playwright-install:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai playwright-install; fi
    uv run --group e2e playwright install chromium

e2e:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai e2e; fi
    just --quiet _task-e2e

[private]
_task-e2e: _task-frontend-build
    #!/usr/bin/env bash
    set -euo pipefail
    echo "🌐 Running Playwright e2e tests..."
    PLAYWRIGHT_BROWSERS_PATH=/cache/shared-ai/ms-playwright \
    uv run --group e2e pytest tests/e2e/ -v -m "slow or e2e" --no-cov

e2e-browser:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai e2e-browser; fi
    just --quiet _task-e2e-browser

[private]
_task-e2e-browser: _task-e2e

openapi-export:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai openapi-export; fi
    uv run python -m pdomain_ocr_trainer_spa.scripts.export_openapi

dev:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai dev; fi
    trap 'kill 0' EXIT
    just --quiet dev-backend &
    just --quiet dev-frontend &
    wait

dev-backend:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai dev-backend; fi
    uv run python -m pdomain_ocr_trainer_spa --reload

dev-frontend:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai dev-frontend; fi
    cd frontend && just --quiet --working-directory . --justfile ../justfile _pnpm run dev

run:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai run; fi
    uv run python -m pdomain_ocr_trainer_spa

doctor:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai doctor; fi
    echo "=== pdomain-ocr-trainer-spa doctor ==="
    uv run python -c "import sys; print('Python:', sys.version)"
    node --version 2>/dev/null && echo "Node: ok" || echo "Node: not found"
    uv run python -c "import pdomain_ops; print('pdomain-ops:', pdomain_ops.__version__)" 2>/dev/null || echo "pdomain-ops: not available"
    uv run python -c "import pdomain_ocr_training; print('pdomain-ocr-training:', pdomain_ocr_training.__version__)" 2>/dev/null || echo "pdomain-ocr-training: not available"
    uv run python -c "import torch; print('CUDA:', torch.cuda.is_available(), '| MPS:', getattr(torch.backends, 'mps', None) and torch.backends.mps.is_available())" 2>/dev/null || echo "torch: not installed (expected — worker subprocess only)"
    HF_TOKEN=~/.huggingface/token; [ -f "$HF_TOKEN" ] && echo "HF token: found" || echo "HF token: not found"

clean:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai clean; fi
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
    rm -rf dist/ frontend/dist/ 2>/dev/null || true
    find src/pdomain_ocr_trainer_spa/static/ -not -name '.gitkeep' -delete 2>/dev/null || true

[default]
ci:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai ci; fi
    just --quiet _task-ci

[private]
_task-ci: setup pre-commit-check lint-check typecheck test _task-frontend-typecheck _task-frontend-test _task-frontend-format-check _task-frontend-lint-check _task-frontend-knip
    #!/usr/bin/env bash
    set -euo pipefail
    docgraph check --strict

ci-full:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai ci-full; fi
    just --quiet _task-ci-full

[private]
_task-ci-full: _task-ci _task-frontend-build _task-e2e _task-build

ci-slow:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai ci-slow; fi
    just --quiet _task-ci-slow

[private]
_task-ci-slow: _task-ci-full

local-setup:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-setup; fi
    ./scripts/local-setup.sh

local-dev:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-dev; fi
    ./scripts/local-dev.sh

local-check:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-check; fi
    ./scripts/local-check.sh

local-upgrade-deps:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-upgrade-deps; fi
    ./scripts/local-upgrade-deps.sh

local-run:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-run; fi
    ./scripts/local-run.sh

local-setup-py:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-setup-py; fi
    ./scripts/local-setup-py.sh

local-frontend-install:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-frontend-install; fi
    ./scripts/local-frontend-install.sh

local-frontend-build:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai local-frontend-build; fi
    just --quiet _task-local-frontend-build

[private]
_task-local-frontend-build: local-frontend-install
    #!/usr/bin/env bash
    set -euo pipefail
    cd frontend && just --quiet --working-directory . --justfile ../justfile _pnpm run build

update-pdomain-deps:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai update-pdomain-deps; fi
    for marker in "${UV_PROJECT_ENVIRONMENT:-.venv}/.pdomain-local-mode" "${UV_PROJECT_ENVIRONMENT:-.venv}/.pdomain-dev-local"; do
        if [[ -f "$marker" ]]; then
            echo "Refusing dependency upgrades while $marker exists" >&2
            exit 1
        fi
    done
    ./scripts/update-pdomain-deps.sh

ci-against-master:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai ci-against-master; fi
    ./scripts/ci-against-master.sh

release-patch:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai release-patch; fi
    BUMP=patch ./scripts/do-release.sh

release-minor:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai release-minor; fi
    BUMP=minor ./scripts/do-release.sh

release-major:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai release-major; fi
    BUMP=major ./scripts/do-release.sh

[private]
_do-release:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai _do-release; fi
    BUMP="${BUMP:-minor}" ./scripts/do-release.sh

lint-check:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai lint-check; fi
    uv run ruff format --check
    uv run ruff check

frontend-lint-check:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ -n "${AI:-}" ]]; then exec just --quiet _ai frontend-lint-check; fi
    just --quiet _task-frontend-lint-check

[private]
_task-frontend-lint-check: frontend-install
    #!/usr/bin/env bash
    set -euo pipefail
    cd frontend
    just --quiet --working-directory . --justfile ../justfile _pnpm exec eslint . --max-warnings 0
