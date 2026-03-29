# ── builder ────────────────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Copy workspace manifest + packages needed to resolve deps
COPY pyproject.toml uv.lock ./
COPY packages/core/ packages/core/
COPY packages/api-client/ packages/api-client/
COPY services/ingestion/ services/ingestion/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package sidekick-ingestion --frozen --no-dev --no-editable

# ── runtime ────────────────────────────────────────────────────────────────────
FROM python:3.13-slim-bookworm

# lxml (Scrapy) needs libxml2 + libxslt at runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY scripts/sfn-run.py /usr/local/bin/sfn-run
RUN chmod +x /usr/local/bin/sfn-run
ENV PATH="/app/.venv/bin:$PATH"

# Install Playwright browser binaries (Chromium + system deps)
RUN playwright install --with-deps chromium