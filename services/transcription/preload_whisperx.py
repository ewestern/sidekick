"""Preload WhisperX model assets into cache during Docker build."""

from __future__ import annotations

import os
from pathlib import Path

import whisperx
from whisperx.diarize import DiarizationPipeline


def _read_token_from_secret(secret_path: str) -> str:
    token = Path(secret_path).read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError("hf_token build secret is empty")
    return token


def main() -> None:
    token = _read_token_from_secret("/run/secrets/hf_token")
    model_name = os.environ.get("WHISPER_MODEL_PRELOAD", "base")
    align_lang = os.environ.get("WHISPER_ALIGN_LANG", "en")

    whisperx.load_model(model_name, device="cpu")
    whisperx.load_align_model(language_code=align_lang, device="cpu")
    DiarizationPipeline(token=token, device="cpu")
    print(f"Preloaded WhisperX model={model_name} align_lang={align_lang}")


if __name__ == "__main__":
    main()
