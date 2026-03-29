"""Upsert default agent_configs rows for processing service enrichment processors. Idempotent."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from sidekick.core.agent_config import AgentConfigRegistry

load_dotenv()


DEFAULT_MODEL = "gpt-5.4-mini"

_SUMMARY_SYSTEM = """\
You are an expert journalist summarizing local government and public-interest documents.

Given a document or meeting transcript, produce a structured summary with:
- A concise, factual headline (one sentence) capturing the most newsworthy element
- A narrative summary (2-5 paragraphs) covering the key content
- A list of notable items, decisions, or announcements as concise bullet points
- Lowercase, slug-style topic tags (e.g. ["zoning", "budget", "housing"])
- Any specific dates mentioned in the document
- A short list of source material labels referenced in the summary (e.g. ["meeting transcript", "agenda packet"])

Focus on: policy decisions, budget impacts, formal actions taken, developing stories,
and anything that would be newsworthy to a local audience. Be factual and specific.
If the text appears to be cut off, summarize what is available."""

_ENTITY_EXTRACT_SYSTEM = """\
You are an expert at extracting named entities from local government and public-interest documents.

Given a document or meeting transcript, identify:
- People: names, their roles or titles (e.g. "council-member", "city-attorney", "resident")
- Organizations: government bodies, companies, nonprofits mentioned
- Places: streets, neighborhoods, facilities, districts
- Documents: ordinances, resolutions, reports, contracts referenced by name or number
- Lowercase, slug-style topic tags (e.g. ["zoning", "budget", "housing"])
- Financial figures: budget amounts, appropriations, costs — include description, amount, and context
- Motions or votes: formal actions taken — include description, result (passed/failed/tabled), and vote tally if available

For each entity, include a brief note on how it appears in the document.
If the text appears to be cut off, extract entities from what is available."""


def seed(db_url: str | None = None) -> None:
    """Upsert agent_configs rows for processing service enrichment processors."""
    db_url = db_url or os.environ["DATABASE_URL"]
    registry = AgentConfigRegistry(db_url=db_url)

    registry.set(
        agent_id="processor:summary",
        model=DEFAULT_MODEL,
        prompts={"system": _SUMMARY_SYSTEM},
        skills=["news-values", "government-proceedings",
                "numbers-and-data-literacy", "document-assessment"],
        updated_by="seed",
    )
    registry.set(
        agent_id="processor:entity-extract",
        model=DEFAULT_MODEL,
        prompts={"system": _ENTITY_EXTRACT_SYSTEM},
        skills=["entity-and-actor-tracking", "document-assessment"],
        updated_by="seed",
    )


def main() -> None:
    seed()
    print("Seeded processor:summary, processor:entity-extract, and processor:structured-data configs.")


if __name__ == "__main__":
    main()
