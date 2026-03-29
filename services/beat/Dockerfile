# ── builder ────────────────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY packages/core/ packages/core/
COPY services/beat/ services/beat/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package sidekick-beat --frozen --no-dev --no-editable

# ── runtime ────────────────────────────────────────────────────────────────────
FROM python:3.13-slim-bookworm

WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY scripts/sfn-run.py /usr/local/bin/sfn-run
RUN chmod +x /usr/local/bin/sfn-run
ENV PATH="/app/.venv/bin:$PATH"
