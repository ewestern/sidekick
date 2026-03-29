# STT image — intended for AWS Batch (g4dn.xlarge spot, CUDA 12.x).
# Do NOT use this image on Fargate; it requires a GPU and is several GB larger
# than the CPU processing image.
#
# ── builder ────────────────────────────────────────────────────────────────────
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04 AS builder

ARG WHISPER_MODEL_PRELOAD=base
ARG WHISPER_ALIGN_LANG=en

# Avoid interactive tzdata debconf during apt (hangs Docker build with no TTY).
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Python 3.13 (Torch-compatible; 3.14 unsupported) via deadsnakes on Ubuntu 22.04
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        software-properties-common curl ca-certificates \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.13 python3.13-dev python3.13-venv \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

# uv's install.sh puts the binary in ~/.local/bin by default (not ~/.cargo/bin).
ENV PATH="/root/.local/bin:/root/.cargo/bin:$PATH"
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON=python3.13
ENV HF_HOME=/opt/hf
ENV HUGGINGFACE_HUB_CACHE=/opt/hf/hub
ENV TRANSFORMERS_CACHE=/opt/hf/transformers
ENV TORCH_HOME=/opt/torch
ENV XDG_CACHE_HOME=/opt/xdg-cache

# Copy workspace manifest + packages needed to resolve deps
COPY pyproject.toml .
COPY packages/core/ packages/core/
COPY services/transcription/ services/transcription/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package sidekick-transcription --no-dev --no-editable

# Preload WhisperX, alignment, and diarization model assets at build time.
# Pass HF token securely: --secret id=hf_token,env=HF_TOKEN
RUN --mount=type=secret,id=hf_token \
    mkdir -p "${HF_HOME}" "${TORCH_HOME}" "${XDG_CACHE_HOME}" \
    && WHISPER_MODEL_PRELOAD="${WHISPER_MODEL_PRELOAD}" \
       WHISPER_ALIGN_LANG="${WHISPER_ALIGN_LANG}" \
       /app/.venv/bin/python /app/services/transcription/preload_whisperx.py

# ── runtime ────────────────────────────────────────────────────────────────────
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.13 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY --from=builder /opt/hf /opt/hf
COPY --from=builder /opt/torch /opt/torch
COPY --from=builder /opt/xdg-cache /opt/xdg-cache
COPY scripts/sfn-run.py /usr/local/bin/sfn-run
RUN chmod +x /usr/local/bin/sfn-run
ENV PATH="/app/.venv/bin:$PATH"
ENV HF_HOME=/opt/hf
ENV HUGGINGFACE_HUB_CACHE=/opt/hf/hub
ENV TRANSFORMERS_CACHE=/opt/hf/transformers
ENV TORCH_HOME=/opt/torch
ENV XDG_CACHE_HOME=/opt/xdg-cache

# No CMD — AWS Batch job definition supplies args after ENTRYPOINT, e.g.:
#   worker --queue-url https://sqs.../transcription
#   transcribe art_a1b2c3
ENTRYPOINT ["sidekick-transcribe"]
