"""Beat agent entry point."""

from __future__ import annotations

import os
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import StoreBackend
from langchain_core.messages import HumanMessage

from sidekick.core.agent_config import AgentConfigRegistry
from sidekick.core.assignment_store import AssignmentStore
from sidekick.core.artifact_store import ArtifactStore

from sidekick.beat.scope import BeatScope, DateWindowScope, EventGroupScope
from sidekick.beat.tools import (
    make_create_research_assignment,
    make_query_artifacts,
    make_write_beat_brief,
    make_write_story_candidate,
)
from sidekick.beat.utils import build_skill_store

DEFAULT_AGENT_ID = "beat-agent:government"


def _resolve_skills_dir(skills_dir: Path | None) -> Path:
    if skills_dir is not None:
        return skills_dir
    env_path = os.environ.get("SKILLS_DIR")
    if env_path:
        return Path(env_path)
    current_directory = os.getcwd()
    return Path(current_directory) / "skills"
    


def _scope_description(scope: BeatScope) -> str:
    if isinstance(scope, EventGroupScope):
        return f"event_group={scope.event_group!r}"
    return f"from {scope.since} to {scope.until}"


def run_beat_agent(
    beat: str,
    geo: str,
    scope: BeatScope,
    artifact_store: ArtifactStore,
    config_registry: AgentConfigRegistry,
    assignment_store: AssignmentStore,
    *,
    agent_id: str = DEFAULT_AGENT_ID,
    skills_dir: Path | None = None,
    created_by: str = "beat-agent",
) -> list[str]:
    """Run the beat agent for a given beat/geo scope.

    Args:
        beat: Beat identifier string (e.g. ``"government:city-council"``).
        geo: Geo identifier string (e.g. ``"us:ca:shasta:redding"``).
        scope: An ``EventGroupScope`` (one event) or ``DateWindowScope`` (assignment window).
        artifact_store: Store used to read inputs and write outputs.
        config_registry: Registry used to resolve model and prompt configuration.
        assignment_store: Store used to create research follow-up assignments.
        agent_id: Agent config ID to resolve from the registry.
        skills_dir: Root directory containing skill subdirectories.
        created_by: Provenance tag written to output artifacts.

    Returns:
        List of artifact IDs written during this run (beat-brief and/or story-candidate artifacts).

    Raises:
        KeyError: If no agent config row exists for ``agent_id``.
    """
    config = config_registry.resolve(agent_id)

    store = (
        build_skill_store(config.skills, _resolve_skills_dir(skills_dir))
        if config.skills
        else None
    )

    derived_ids: list[str] = []
    written_ids: list[str] = []

    tools = [
        make_query_artifacts(artifact_store, beat, geo, scope, derived_ids),
        make_write_beat_brief(artifact_store, beat, geo,
                              scope, derived_ids, written_ids, created_by),
        make_write_story_candidate(artifact_store, beat, geo, scope,
                                   derived_ids, written_ids, created_by),
        make_create_research_assignment(
            assignment_store,
            beat,
            geo,
            scope,
            derived_ids,
            created_by,
        ),
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
        f"Analyze recent developments for beat={beat!r}, geo={geo!r}, "
        f"{_scope_description(scope)}. "
        "Use query_artifacts to retrieve source material and broader beat context before "
        "writing a beat-brief covering notable developments. "
        "If a development is draft-worthy, write a structured story-candidate. "
        "If important follow-up context is missing, create a research assignment. "
        "Do not create a story-candidate when the development is routine or under-evidenced."
    )
    agent.invoke({"messages": [HumanMessage(content=initial_message)]})

    return list(written_ids)
