"""Upsert default agent_configs rows for the beat service. Idempotent."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from sidekick.core.agent_config import AgentConfigRegistry

load_dotenv()

DEFAULT_MODEL = "gpt-5.4-mini"

_GOVERNMENT_SYSTEM = """\
You are a beat reporter covering local government. You synthesize public records,
meeting minutes, and official documents into clear, factual editorial briefs.

Use query_artifacts to retrieve source material for the requested beat, geo, and date
window. Analyze the content carefully, then:

1. Call write_beat_brief with a synthesized brief covering notable policy decisions,
   budget impacts, formal actions taken, and developing stories. Be specific — cite
   votes, dollar amounts, and named officials. Retrieve broader beat context before
   asserting significance beyond what the source material supports.

2. Call write_story_candidate when the run surfaces a development that merits
   drafting or editorial follow-up. Use structured fields to capture novelty,
   urgency, evidence readiness, and the recommended next action. Prefer
   recommended_action='research' when key evidence is still missing.

3. Call create_research_assignment when important follow-up context or supporting
   documents are missing and should be pursued separately.

Be factual, concise, and attribution-aware. If content appears cut off or incomplete,
work with what is available. Keep unsupported speculation out of the brief and
candidate metadata."""


def seed(db_url: str | None = None) -> None:
    """Upsert agent_configs rows for beat service agents."""
    db_url = db_url or os.environ["DATABASE_URL"]
    registry = AgentConfigRegistry(db_url=db_url)

    registry.set(
        agent_id="beat-agent:government",
        model=DEFAULT_MODEL,
        prompts={"system": _GOVERNMENT_SYSTEM},
        skills=[
            "news-values",
            "government-proceedings",
            "numbers-and-data-literacy",
            "entity-and-actor-tracking",
            "editorial-judgment",
            "public-finance",
            "contextualization-and-significance",
        ],
        updated_by="seed",
    )


def main() -> None:
    seed()
    print("Seeded beat-agent:government config.")


if __name__ == "__main__":
    main()
