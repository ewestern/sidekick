# ── builder ────────────────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Copy workspace manifest + packages needed to resolve deps
COPY pyproject.toml .
COPY uv.lock .
COPY packages/core/ packages/core/
COPY services/api/ services/api/
COPY migrations/ migrations/
# migrations/ is a workspace package — uv installs it into .venv

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package sidekick-api --no-dev --no-editable

# ── runtime ────────────────────────────────────────────────────────────────────
FROM python:3.13-slim-bookworm

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/.venv .venv
ENV PATH="/app/.venv/bin:$PATH"