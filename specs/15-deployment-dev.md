# 15 — Deployment + dev

How to set up the dev environment, what `make` does, how the wheel
ships SPA bundle bytes, and what GPU / MPS quirks to expect.

> Required reading: [`02-backend.md`](02-backend.md),
> [`03-frontend.md`](03-frontend.md),
> [workspace release-strategy memory](../../README.md#release).

---

## 1. Repo layout (top level)

```
pdomain-ocr-trainer-spa/
├── README.md
├── DEVELOPMENT.md                  (M0 — quickstart for contributors)
├── Dockerfile                      (multi-stage: deps → frontend-build → wheel-build → runtime)
├── Makefile
├── mise.toml                       (Node 24, Python 3.13)
├── pyproject.toml                  (hatchling + hatch-vcs; force-include static dir)
├── uv.lock
├── install.sh / install.ps1
├── build_hooks/
│   └── spa_check.py                (build-time assertion: SPA bytes are inside the wheel)
├── .github/workflows/
│   ├── ci.yml                      (every PR: lint, test, e2e, wheel-build)
│   ├── release.yml                 (on tag: build wheel + sdist, attach to GH Release, push to pdomain-index)
│   └── nightly.yml                 (slow tests + HF mock refresh)
├── .pre-commit-config.yaml
├── .gitignore
├── specs/                          (this directory)
├── src/pdomain_ocr_trainer_spa/         (Python package)
├── frontend/                       (Vite / React)
└── tests/
```

---

## 2. Tooling versions

`mise.toml`:

```toml
[tools]
python = "3.13"
node = "24"

[env]
UV_LINK_MODE = "copy"
```

uv handles Python deps; npm handles frontend deps. Pre-commit
hooks run both.

Pinning rationale matches `pdomain-ocr-labeler-spa/specs/15-deployment-dev.md`
— Node 24 because pgdp-prep is on it; Python 3.13 because
`pdomain-book-tools` is on it.

---

## 3. Makefile targets

```
make setup                   # uv sync + npm ci (in frontend/)
make install                 # equivalent to setup but also installs the local package via uv sync
make lint                    # ruff + eslint
make typecheck               # pyright + tsc
make test                    # pytest (excludes -m slow)
make test-slow               # pytest -m slow
make frontend-test           # vitest --run
make frontend-build          # vite build → frontend/dist + copy into src/pdomain_ocr_trainer_spa/static
make build                   # python -m build (wheel + sdist); fails if static/ is empty (build_hooks/spa_check.py)
make e2e                     # playwright test
make openapi-export          # python -m pdomain_ocr_trainer_spa.scripts.export_openapi → frontend/openapi.json + types.ts
make dev                     # start backend (uvicorn --reload) and frontend (vite dev) concurrently
make dev-backend             # uvicorn only
make dev-frontend            # vite only
make clean                   # rm dist/, frontend/dist, src/.../static, .ruff_cache, etc.
make doctor                  # diagnostic; prints versions, paths, GPU info, HF token presence
```

`make dev` listens on:

- backend: `127.0.0.1:8081` (different from labeler-spa 8080).
- frontend: `127.0.0.1:5174` (different from pgdp-prep 5173).

Both ports configurable via env.

---

## 4. Wheel-with-SPA assertion

`build_hooks/spa_check.py` runs as a hatch build hook:

1. Reads `src/pdomain_ocr_trainer_spa/static/index.html`.
2. Asserts presence and non-empty.
3. Asserts at least one `assets/*.js` and `assets/*.css` referenced
   from index.html exists.
4. Fails the build with a clear message if missing.

Force-include in `pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/pdomain_ocr_trainer_spa"]
force-include = { "src/pdomain_ocr_trainer_spa/static" = "pdomain_ocr_trainer_spa/static" }
```

Verify post-build:

```bash
python -m zipfile -l dist/pdomain_ocr_trainer_spa-*.whl | grep static/index.html
```

---

## 5. Devcontainer

`/.devcontainer/devcontainer.json` (lives in the workspace root,
not this repo) already pins Python + Node. This repo adds nothing
to the devcontainer beyond what the workspace provides.

GPU access in the devcontainer is host-dependent. The repo's
`make doctor` reports CUDA + MPS availability so users see at
boot whether training will work.

---

## 6. Install for end users

Two paths:

### 6.1 `uv tool install` from a local wheel

```
uv tool install ./dist/pdomain_ocr_trainer_spa-*.whl
pdomain-ocr-trainer-ui --port 8081
```

### 6.2 `uv tool install` from the pdomain-index PEP 503 index

Per workspace `project_release_strategy.md` memory:

```
uv tool install --index https://pdomain.github.io/pdomain-index-pip pdomain-ocr-trainer-spa
```

The `pdomain-index` repo isn't built yet — when it lands, this repo's
`release.yml` pushes wheels there in addition to the GitHub
Release attachment.

### 6.3 Bash + PowerShell installers

`install.sh` / `install.ps1` shell out to `uv tool install` with
the `pdomain-index` URL. Mirrors the labeler-spa installers.

---

## 7. CLI entry point

`pyproject.toml`:

```toml
[project.scripts]
pdomain-ocr-trainer-ui = "pdomain_ocr_trainer_spa.__main__:main"
```

`__main__:main`:

1. Parse `--host`, `--port`, `--no-browser`, `--log-level`.
2. Read env into `Settings()`.
3. `uvicorn.run(build_app(settings), ...)`.
4. Open browser at `http://{host}:{port}/` after a 1 s delay
   unless `--no-browser`.

The legacy `pdomain-ocr-training` keeps its own entry point under a
different name so both can coexist.

---

## 8. GPU / MPS notes

Detection + recognition training reaches DocTR through
`pdomain-ocr-training`, run inside the worker subprocess
([`02-backend.md`](02-backend.md) §5, D-T1). The long-lived FastAPI
process **never imports `torch`** — only the worker does.

- Device discovery (`GET /api/runtime/devices`) goes through
  `pdomain-ocr-ops` (`pdomain_ocr_ops.gpu`, `pick_device`), not a SPA-local
  torch probe. The endpoint result is cached.
- CUDA: the worker uses whatever `pdomain-ocr-training` + DocTR support;
  `CreateRunRequest.device` pins a GPU index.
- MPS: opportunistically offered in the device dropdown when the
  platform reports it available; some DocTR ops fall back to CPU
  and stay slow. A banner warns if the user pins `mps` with an arch
  known to be slow on CPU fallback (see the
  [deferred MPS guidance](../docs/context/intent-map.md)).
- CPU: supported, but only useful for tiny smoke runs.

---

## 9. DocTR dependency

There is **no doctr clone or submodule** (D-T9). DocTR is a normal
dependency of `pdomain-ocr-training`, declared in that package's
`pyproject.toml`; `uv` resolves it transitively. Any `CUSTOM:` vocab
handling is entirely a `pdomain-ocr-training` concern — the SPA neither
clones, vendors, nor patches doctr. (The
[DocTR dependency decision](17-decisions.md#d-t9-doctr-is-a-dependency-of-pdomain-ocr-training) records why the earlier
clone question is resolved.)

---

## 10. CI workflows

### 10.1 `ci.yml`

```yaml
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - uses: jdx/mise-action@v2
      - run: make setup
      - run: make lint
      - run: make typecheck
      - run: make test
      - run: make frontend-test
      - run: make frontend-build
      - run: make e2e
      - run: make build
```

### 10.2 `release.yml`

Tag-driven (`v0.x.y`). Builds wheel + sdist, runs the same gates
as `ci.yml`, then:

- Creates a GitHub Release with the wheel attached.
- (Future) Pushes wheel to `pdomain-index` repo's PEP 503 tree.

Two-pass `npm install` lesson from
`pdomain-ocr-labeler-spa/specs/15-deployment-dev.md` (B-28 + B-19) is
inherited here: dockerfile and CI both `npm install` once during
deps stage and once after lockfile, to converge on the lockfile
before builds.

### 10.3 `nightly.yml`

Cron-scheduled. Runs `make test-slow` and re-records HF mocks if
they drift. Failure: opens a draft issue.

---

## 11. Pre-commit

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: vX.Y.Z
    hooks: [ruff, ruff-format]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: vX.Y.Z
    hooks: [trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files]
  - repo: local
    hooks:
      - id: eslint
        name: eslint
        entry: bash -lc "cd frontend && npx eslint --max-warnings=0"
        language: system
        files: ^frontend/.*\.(ts|tsx)$
      - id: openapi-drift
        name: openapi drift
        entry: bash -lc "make openapi-export && git diff --exit-code frontend/openapi.json frontend/src/api/types.ts"
        language: system
        pass_filenames: false
```

---

## 12. Acceptance behaviour

1. Fresh clone → `make setup` → `make test` → green.
2. `make dev` → backend at 8081, vite at 5174. Open browser; SPA
   loads, calls `/api/profiles`, shows `all` profile.
3. `make build` → wheel under `dist/`. `python -m zipfile -l` shows
   `pdomain_ocr_trainer_spa/static/index.html` present.
4. `uv tool install ./dist/...whl` → `pdomain-ocr-trainer-ui --port 8081`
   serves both API and SPA from one process.
5. `make doctor` reports CUDA: yes/no, MPS: yes/no, HF token:
   yes/no, and the resolved `pdomain-ocr-training` / `pdomain-ocr-ops`
   versions.

---

## 13. Citations

- Wheel-with-SPA pattern: `pdomain-ocr-labeler-spa/specs/15-deployment-dev.md`.
- Two-pass npm install: same spec + commit `eba093e`.
- DocTR as a `pdomain-ocr-training` dependency: D-T9
  ([`17-decisions.md`](17-decisions.md)).
- Release strategy: workspace memory `project_release_strategy.md`.
