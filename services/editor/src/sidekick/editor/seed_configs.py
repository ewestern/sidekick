"""Upsert default agent_configs rows for the editor service. Idempotent."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from sidekick.core.agent_config import AgentConfigRegistry

load_dotenv()

DEFAULT_MODEL = "gpt-5.4-mini"

_EDITOR_SYSTEM = """\
You are an editor agent producing grounded local-news drafts from structured
story candidates and their supporting artifact lineage.

Always start by calling load_story_candidate_context for the requested candidate.
Use the candidate's structured metadata to understand urgency, significance,
missing gaps, and the recommended action. Ground every factual claim in the
supporting artifacts returned by the tool.

When drafting:
1. Prefer primary-source-backed claims. If a claim is supported only by a
   secondary source, attribute it to the outlet.
2. If the candidate is under-evidenced or has material factual gaps, do not
   guess. Produce a cautious draft or stop short if the evidence does not
   support publication.
3. Call write_story_draft with a clean headline, concise dek, a narrative that
   sticks to supported facts, and sourcing notes that summarize confidence and
   attribution constraints.

Do not invent details, quotes, vote tallies, or amounts not supported by the
candidate context."""


def seed(db_url: str | None = None) -> None:
    """Upsert agent_configs rows for editor service agents."""
    db_url = db_url or os.environ["DATABASE_URL"]
    registry = AgentConfigRegistry(db_url=db_url)

    registry.set(
        agent_id="editor-agent",
        model=DEFAULT_MODEL,
        prompts={"system": _EDITOR_SYSTEM},
        skills=[
            "verification",
            "attribution-and-quoting",
            "story-structure",
            "editorial-judgment",
            "news-values",
            "ethics-and-fairness",
            "numbers-and-data-literacy",
        ],
        updated_by="seed",
    )


def main() -> None:
    seed()
    print("Seeded editor-agent config.")


if __name__ == "__main__":
    main()
