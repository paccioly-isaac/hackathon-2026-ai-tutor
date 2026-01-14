# Build stage - with all compilation tools
# Using slim (Debian) instead of Alpine for better compatibility with scientific packages
FROM python:3.13-slim AS builder

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/usr/src/.venv \
    UV_CACHE_DIR=/var/.cache/uv

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.8.4 /uv /uvx /bin/

# Install build dependencies (minimal - most packages have wheels for Debian)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files needed for dependency installation
COPY pyproject.toml uv.lock ./

# Copy src directory (needed for editable install of the project package)
COPY src/ ./src/

# Install dependencies
RUN --mount=type=cache,target=/var/.cache/uv \
    uv sync --frozen --no-dev

# Runtime stage - minimal image
FROM python:3.13-slim

WORKDIR /usr/src/app

ARG APP_VERSION=latest

ENV APP_NAME=agentic-ai-tutor \
    APP_VERSION=$APP_VERSION \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/usr/src/.venv \
    SRC_CODE_PATH=/usr/src/app

# Install runtime dependencies
# - libffi8, libssl3: for cryptography and SSL connections
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from builder
COPY --from=builder /usr/src/.venv /usr/src/.venv

# Add venv bin to PATH and project root to PYTHONPATH (for src.* imports)
ENV PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}" \
    PYTHONPATH="/usr/src/app:${PYTHONPATH}"

# Copy application code
COPY ./ ./

# Run FastAPI server with uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]