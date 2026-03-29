"""Embedding utilities for the Sidekick pipeline.

All embedding calls go through :func:`build_embed_fn`. This is the only
place in the codebase that touches the embeddings API — agents and services
receive the returned callable as an injected dependency.

Model: ``text-embedding-3-small`` (1536-dim). Dimension is baked into the
artifact store schema (``vector(1536)``); changing it requires a migration.
"""

from __future__ import annotations

import os
from typing import Callable

import openai


def build_embed_fn() -> Callable[[str], list[float]]:
    """Return a function that embeds a string using OpenAI text-embedding-3-small.

    Reads ``OPENAI_API_KEY`` from the environment and fails immediately if it
    is not set — there is no silent fallback. Call this once at service startup
    and inject the result into :class:`~sidekick.core.artifact_store.ArtifactStore`.

    Returns:
        A callable ``(text: str) -> list[float]`` that returns a 1536-dim vector.

    Raises:
        KeyError: If ``OPENAI_API_KEY`` is not set in the environment.
    """
    api_key = os.environ["OPENAI_API_KEY"]
    client = openai.OpenAI(api_key=api_key)

    def embed(text: str) -> list[float]:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return response.data[0].embedding

    return embed
