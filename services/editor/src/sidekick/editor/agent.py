"""Editor agent entry point."""

from __future__ import annotations

import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import StoreBackend
from langchain_core.messages import HumanMessage

from sidekick.core.agent_config import AgentConfigRegistry
from sidekick.core.artifact_store import ArtifactStore

from sidekick.editor.tools import (
    make_load_story_candidate_context,
    make_write_story_draft,
)
from sidekick.editor.utils import build_skill_store

DEFAULT_AGENT_ID = "editor-agent"


def _resolve_skills_dir(skills_dir: Path | None) -> Path:
    if skills_dir is not None:
        return skills_dir
    env_path = os.environ.get("SKILLS_DIR")
    if env_path:
        return Path(env_path)
    current_directory = os.getcwd()
    return Path(current_directory) / "skills"


def run_editor_agent(
    candidate_id: str,
    artifact_store: ArtifactStore,
    config_registry: AgentConfigRegistry,
    *,
    db_url: str,
    agent_id: str = DEFAULT_AGENT_ID,
    skills_dir: Path | None = None,
    created_by: str = "editor-agent",
) -> list[str]:
    """Run the editor agent for a given story-candidate artifact."""
    config = config_registry.resolve(agent_id)
    store = (
        build_skill_store(config.skills, _resolve_skills_dir(skills_dir))
        if config.skills
        else None
    )

    loaded_candidate_ids: list[str] = []
    written_ids: list[str] = []
    tools = [
        make_load_story_candidate_context(artifact_store, db_url, loaded_candidate_ids),
        make_write_story_draft(artifact_store, written_ids, created_by),
    ]

    agent = create_deep_agent(
        model=config.model,
        tools=tools,
        system_prompt=config.prompts["system"],
        skills=["/skills/"] if config.skills else None,
        backend=StoreBackend,
        store=store,
    )
    initial_message = (
        f"Draft a story from candidate_id={candidate_id!r}. "
        "Start by loading the story candidate context, then write a grounded story draft."
    )
    agent.invoke({"messages": [HumanMessage(content=initial_message)]})
    return list(written_ids)
