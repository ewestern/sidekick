"""Pydantic output schemas for LLM-based enrichment processors."""

from __future__ import annotations

from pydantic import BaseModel


class SummarySourceReference(BaseModel):
    """Source materials explicitly relied on in the summary."""

    label: str
    """Human-readable source label, e.g. "meeting transcript" or "agenda packet".""" 


class SummaryOutput(BaseModel):
    """Structured summary of a government or public-interest document or transcript."""

    headline: str
    """One-sentence headline capturing the most newsworthy element."""

    summary: str
    """2-5 paragraph narrative summary of the document or meeting."""

    key_developments: list[str]
    """Notable items, decisions, or announcements as concise bullet points."""

    topics: list[str]
    """Lowercase, slug-style topic tags (e.g. ["zoning", "budget", "housing"])."""

    date_references: list[str]
    """Dates mentioned in the document (e.g. ["2026-03-11", "April 15, 2026"])."""

    source_references: list[SummarySourceReference]
    """Source materials referenced in the summary for rendering a Sources section."""


class Entity(BaseModel):
    """A named entity extracted from a document or transcript."""

    name: str
    """Canonical name of the entity."""

    type: str
    """Entity type: person | organization | place | document | topic | financial."""

    role: str | None = None
    """Contextual role (e.g. "council-member", "department-head", "contractor")."""

    context: str | None = None
    """Brief note on how this entity appears in the document."""


class EntityExtractionOutput(BaseModel):
    """Named entities and key references extracted from a document or transcript."""

    entities: list[Entity]
    """People, organizations, places, and documents referenced in the text."""

    topics: list[str]
    """Lowercase, slug-style topic tags for filtering and retrieval."""

    financial_figures: list[dict[str, str]]
    """Financial amounts with context, e.g. [{"description": "FY2027 budget", "amount": "$4.2M", "context": "proposed increase"}]."""

    motions_or_votes: list[dict[str, str]]
    """Formal actions taken, e.g. [{"description": "Approve Ordinance 2026-14", "result": "passed", "vote_tally": "5-2"}]."""
