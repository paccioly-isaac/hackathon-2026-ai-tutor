# Build stage - with all compilation tools
# Using slim (Debian) instead of Alpine for better compatibility with scientific packages
FROM python:3.13-slim AS builder

WORKDIR /usr/src/project

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

WORKDIR /usr/src/project

ARG WITH_NEW_RELIC=false
ARG APP_VERSION=latest

ENV APP_NAME=ia-lms-redacoes \
    APP_VERSION=$APP_VERSION \
    WITH_NEW_RELIC=$WITH_NEW_RELIC \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/usr/src/.venv \
    SRC_CODE_PATH=/usr/src/project

# Install runtime dependencies
# - libffi8, libssl3: for cryptography
# - libgl1, libglib2.0-0: for opencv-python-headless
# - libjpeg62, libpng16-16, zlib1g: for pillow image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 \
    libssl3 \
    libgl1 \
    libglib2.0-0 \
    libjpeg62-turbo \
    libpng16-16 \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from builder
COPY --from=builder /usr/src/.venv /usr/src/.venv

# Add venv bin to PATH
ENV PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}"

# Copy application code
COPY ./ ./

# Run FastAPI server with uvicorn
CMD ["uvicorn", "ia_lms_redacoes.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
