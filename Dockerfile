# Multi-stage: deps → frontend-build → wheel-build → runtime
# Stage 1: Python deps + frontend build
FROM python:3.13-slim AS builder

# Install Node 24 via nvm
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
ENV NVM_DIR=/root/.nvm
RUN curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash \
    && . "$NVM_DIR/nvm.sh" \
    && nvm install 24 \
    && nvm use 24

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy Python project files
COPY pyproject.toml uv.lock ./
COPY src/ src/

# Install Python dependencies from the lockfile and configured indexes.
RUN uv sync --frozen --no-dev

# Copy frontend source
COPY frontend/ frontend/

# Build frontend (uses PATH node/npm from nvm)
SHELL ["/bin/bash", "-c"]
RUN . "$NVM_DIR/nvm.sh" && nvm use 24 && cd frontend && npm install && npm run build

# Build wheel
RUN uv build --wheel

# Stage 2: Runtime
FROM python:3.13-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY --from=builder /app/dist/*.whl .

RUN uv tool install *.whl

EXPOSE 8081

ENTRYPOINT ["pdomain-ocr-trainer-ui", "--host", "0.0.0.0", "--port", "8081", "--no-browser"]
