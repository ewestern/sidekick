"""Editor service utilities."""

from __future__ import annotations

from pathlib import Path

from deepagents.backends.utils import create_file_data
from langgraph.store.memory import InMemoryStore

from sidekick.core.skills import load_skills_from_disk


def build_skill_store(skill_ids: list[str], skills_dir: Path) -> InMemoryStore:
    """Load named skills into an ephemeral InMemoryStore for StoreBackend."""
    store = InMemoryStore()
    for key, content in load_skills_from_disk(skill_ids, skills_dir).items():
        store.put(("filesystem",), key, create_file_data(content))
    return store
