AI ?=
LOG := .ci-ai.log

ifdef AI
_goals := $(or $(MAKECMDGOALS),ci)
.PHONY: $(_goals)
$(_goals):
	@rm -f $(LOG)
	@$(MAKE) --no-print-directory AI= $@ > $(LOG) 2>&1 \
		&& echo "✅ $@ passed (log: $(LOG))" \
		|| (echo "❌ $@ failed:"; grep -E "(FAILED|ERROR|error|Error)" $(LOG) | head -30; echo "(full log: $(LOG))"; exit 1)

else

MISE := $(shell command -v mise 2>/dev/null || echo $$HOME/.local/bin/mise)
HAVE_MISE = [ -x "$(MISE)" ]
MISE_RUN = if $(HAVE_MISE); then $(MISE) exec --; fi

# Run pnpm through mise if available, else fall back to PATH pnpm/npm
define _pnpm
	if $(HAVE_MISE); then \
		$(MISE) exec -- pnpm $(1); \
	elif command -v pnpm >/dev/null 2>&1; then \
		pnpm $(1); \
	else \
		echo "❌ no pnpm/mise available. Run 'make mise-setup' or install Node."; \
		exit 1; \
	fi
endef

.PHONY: help setup install uninstall remove-venv reset lint format typecheck \
        pre-commit-check test test-slow e2e e2e-browser frontend-install \
        frontend-test frontend-build build clean ci ci-full upgrade-deps \
        openapi-export dev dev-backend dev-frontend doctor mise-setup

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

mise-setup: ## Install mise tooling (Node 24, Python 3.13)
	$(MISE) install

setup: ## Sync Python deps + install pre-commit hooks
	@echo "📦 Installing dependencies..."
	uv sync --group dev
	@echo "🪝 Setting up pre-commit hooks..."
	uv run pre-commit install || true
	@echo "✅ Setup complete!"

install: setup ## Alias for setup

uninstall: ## Remove the installed pd-ocr-trainer-spa uv tool
	@uv tool uninstall pd-ocr-trainer-spa || true
	@echo "✅ pd-ocr-trainer-spa uninstalled."

remove-venv: ## Remove the virtual environment
	rm -rf .venv

reset: clean remove-venv setup ## Rebuild the virtual environment
	@echo "✅ Environment Reset!"

upgrade-deps: ## Upgrade dependencies and sync local environment
	@echo "⬆️ Upgrading dependency lockfile..."
	uv lock --upgrade
	@echo "📦 Syncing upgraded dependencies..."
	uv sync --group dev
	@echo "✅ Dependencies upgraded and environment synced!"

# ---------------------------------------------------------------------------
# Lint / format / typecheck / test
# ---------------------------------------------------------------------------

lint: ## Run ruff checks
	uv run ruff check --select I --fix
	uv run ruff check --fix

format: ## Format code with ruff
	uv run ruff format
	@$(MAKE) --no-print-directory lint

typecheck: ## Run basedpyright at recommended mode
	uv run basedpyright src/pd_ocr_trainer_spa --level error

pre-commit-check: ## Run pre-commit on all files
	uv run pre-commit run --all-files

test: ## Run pytest (excludes slow/e2e tests)
	uv run pytest tests/ -v -n auto

test-slow: ## Run slow tests (real subprocess + HF mocks)
	uv run pytest tests/ -v -m slow

frontend-install: ## Install frontend dependencies
	cd frontend && CI=true $(call _pnpm,install --frozen-lockfile) || cd frontend && $(call _pnpm,install)

frontend-test: frontend-install ## Run frontend vitest suite
	cd frontend && node_modules/.bin/vitest run

frontend-build: frontend-install ## Build the React/Vite SPA to src/pd_ocr_trainer_spa/static/
	cd frontend && $(call _pnpm,run build)

build: ## Build wheel + sdist (requires frontend-build first)
	uv run python -m build

e2e: frontend-build ## Run Playwright browser e2e tests (requires chromium)
	@echo "🌐 Running Playwright e2e tests..."
	PLAYWRIGHT_BROWSERS_PATH=/cache/shared-ai/ms-playwright \
	uv run --group e2e pytest tests/e2e/ -v -m "slow or e2e" --no-cov

e2e-browser: e2e ## Alias for e2e

openapi-export: ## Export OpenAPI JSON + generate TypeScript types
	uv run python -m pd_ocr_trainer_spa.scripts.export_openapi

dev: ## Start backend + frontend dev servers concurrently
	@echo "🚀 Starting backend on :8081 and frontend on :5174"
	@trap 'kill 0' EXIT; \
	$(MAKE) --no-print-directory dev-backend & \
	$(MAKE) --no-print-directory dev-frontend & \
	wait

dev-backend: ## Start uvicorn backend (--reload)
	uv run uvicorn "pd_ocr_trainer_spa.bootstrap:build_app" \
		--factory --host 127.0.0.1 --port 8081 --reload

dev-frontend: ## Start Vite dev server
	cd frontend && $(call _pnpm,run dev)

doctor: ## Print versions, paths, GPU info, HF token presence
	@echo "=== pd-ocr-trainer-spa doctor ==="
	@uv run python -c "import sys; print('Python:', sys.version)"
	@node --version 2>/dev/null && echo "Node: ok" || echo "Node: not found"
	@uv run python -c "import pd_ocr_ops; print('pd-ocr-ops:', pd_ocr_ops.__version__)" 2>/dev/null || echo "pd-ocr-ops: not available"
	@uv run python -c "import pd_ocr_training; print('pd-ocr-training:', pd_ocr_training.__version__)" 2>/dev/null || echo "pd-ocr-training: not available"
	@uv run python -c "import torch; print('CUDA:', torch.cuda.is_available(), '| MPS:', getattr(torch.backends, 'mps', None) and torch.backends.mps.is_available())" 2>/dev/null || echo "torch: not installed (expected — worker subprocess only)"
	@HF_TOKEN=~/.huggingface/token; [ -f "$$HF_TOKEN" ] && echo "HF token: found" || echo "HF token: not found"

clean: ## Clean cache + build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ frontend/dist/ 2>/dev/null || true
	find src/pd_ocr_trainer_spa/static/ -not -name '.gitkeep' -delete 2>/dev/null || true

ci: setup lint typecheck test frontend-install frontend-test ## CI pipeline (without frontend-build/e2e/wheel)

ci-full: ci frontend-build e2e build ## Full CI including frontend build, e2e, and wheel

endif
