# 15 — Deployment + dev

How to set up the dev environment, what `make` does, how the wheel
ships SPA bundle bytes, and what GPU / MPS quirks to expect.

> Required reading: [`02-backend.md`](02-backend.md),
> [`03-frontend.md`](03-frontend.md),
> [workspace release-strategy memory](../../README.md#release).

---

## 1. Repo layout (top level)

```
pd-ocr-trainer-spa/
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
│   ├── release.yml                 (on tag: build wheel + sdist, attach to GH Release, push to pd-index)
│   └── nightly.yml                 (slow tests + HF mock refresh)
├── .pre-commit-config.yaml
├── .gitignore
├── specs/                          (this directory)
├── OPEN_QUESTIONS.md
├── src/pd_ocr_trainer_spa/         (Python package)
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

Pinning rationale matches `pd-ocr-labeler-spa/specs/15-deployment-dev.md`
— Node 24 because pgdp-prep is on it; Python 3.13 because
`pd-book-tools` is on it.

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
make frontend-build          # vite build → frontend/dist + copy into src/pd_ocr_trainer_spa/static
make build                   # python -m build (wheel + sdist); fails if static/ is empty (build_hooks/spa_check.py)
make e2e                     # playwright test
make openapi-export          # python -m pd_ocr_trainer_spa.scripts.export_openapi → frontend/openapi.json + types.ts
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

1. Reads `src/pd_ocr_trainer_spa/static/index.html`.
2. Asserts presence and non-empty.
3. Asserts at least one `assets/*.js` and `assets/*.css` referenced
   from index.html exists.
4. Fails the build with a clear message if missing.

Force-include in `pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/pd_ocr_trainer_spa"]
force-include = { "src/pd_ocr_trainer_spa/static" = "pd_ocr_trainer_spa/static" }
```

Verify post-build:

```bash
python -m zipfile -l dist/pd_ocr_trainer_spa-*.whl | grep static/index.html
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
uv tool install ./dist/pd_ocr_trainer_spa-*.whl
pd-ocr-trainer-ui --port 8081
```

### 6.2 `uv tool install` from the pd-index PEP 503 index

Per workspace `project_release_strategy.md` memory:

```
uv tool install --index https://concavetrillion.github.io/pd-index pd-ocr-trainer-spa
```

The `pd-index` repo isn't built yet — when it lands, this repo's
`release.yml` pushes wheels there in addition to the GitHub
Release attachment.

### 6.3 Bash + PowerShell installers

`install.sh` / `install.ps1` shell out to `uv tool install` with
the `pd-index` URL. Mirrors the labeler-spa installers.

---

## 7. CLI entry point

`pyproject.toml`:

```toml
[project.scripts]
pd-ocr-trainer-ui = "pd_ocr_trainer_spa.__main__:main"
```

`__main__:main`:

1. Parse `--host`, `--port`, `--no-browser`, `--log-level`.
2. Read env into `Settings()`.
3. `uvicorn.run(build_app(settings), ...)`.
4. Open browser at `http://{host}:{port}/` after a 1 s delay
   unless `--no-browser`.

The legacy `pd-ocr-trainer` keeps its own entry point under a
different name so both can coexist.

---

## 8. GPU / MPS notes

Detection + recognition training reaches DocTR through
`pd_ocr_trainer.train_*`. The SPA delegates **all** GPU concerns
to that subprocess. The SPA backend itself never imports torch
( beyond tiny inspection paths under `core/runtime.py` for the
device-discovery endpoint, which is gated behind a try/except).

- CUDA: works as it does for the legacy trainer.
- MPS: per `pd-ocr-trainer/README.md` "Mac / Apple Silicon (MPS)
  support" is in-progress in the trainer; the SPA opportunistically
  offers `mps` in the device dropdown when `torch.backends.mps.is_available()`,
  but the operations that fall back to CPU are still slow. Banner
  warning if the user picks `mps` and selects an arch known to be
  slow on CPU fallback ([Q25](../OPEN_QUESTIONS.md)).
- CPU: supported but only useful for tiny smoke runs.

The device-discovery endpoint (`GET /api/runtime/devices`) imports
torch lazily and caches the result; first hit may take a few
hundred ms.

---

## 9. doctr submodule

The legacy trainer requires the user to clone
`mindee/doctr` next to the repo and patch `train_pytorch.py` to
support the `CUSTOM:` vocab prefix (see `pd-ocr-trainer/README.md`).

The SPA depends on the same patched doctr clone. Two options:

- **(A)** Same external clone as legacy. Document under
  DEVELOPMENT.md; `make doctor` checks the path.
- **(B)** Vendor a fork in the SPA repo as a git submodule.

Recommendation: **(A)** for v1 — vendoring breaks the legacy
trainer if both are on the same machine. ([Q26](../OPEN_QUESTIONS.md))

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
- (Future) Pushes wheel to `pd-index` repo's PEP 503 tree.

Two-pass `npm install` lesson from
`pd-ocr-labeler-spa/specs/15-deployment-dev.md` (B-28 + B-19) is
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
   `pd_ocr_trainer_spa/static/index.html` present.
4. `uv tool install ./dist/...whl` → `pd-ocr-trainer-ui --port 8081`
   serves both API and SPA from one process.
5. `make doctor` reports CUDA: yes/no, MPS: yes/no, HF token: yes/no,
   doctr clone path: present/missing.

---

## 13. Citations

- Wheel-with-SPA pattern: `pd-ocr-labeler-spa/specs/15-deployment-dev.md`.
- Two-pass npm install: same spec + commit `eba093e`.
- doctr clone + patch: `pd-ocr-trainer/README.md`.
- Release strategy: workspace memory `project_release_strategy.md`.
