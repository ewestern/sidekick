"""Controlled vocabulary for artifact fields and routing keys.

Stage, ArtifactStatus, ContentType, and ProcessingProfile are StrEnum classes — values
compare equal to their string equivalents, and Pydantic coerces plain strings automatically
at model construction. Beat and geo routing keys are validated against their respective trees.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema


class Stage(StrEnum):
    RAW = "raw"
    PROCESSED = "processed"
    ANALYSIS = "analysis"
    CONNECTIONS = "connections"
    DRAFT = "draft"


class ArtifactStatus(StrEnum):
    ACTIVE = "active"
    PENDING_ACQUISITION = "pending_acquisition"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"


class ContentType(StrEnum):
    DOCUMENT_RAW = "document-raw"
    AUDIO_RAW = "audio-raw"
    VIDEO_RAW = "video-raw"
    DOCUMENT_TEXT = "document-text"
    ENTITY_EXTRACT = "entity-extract"
    STRUCTURED_DATA = "structured-data"
    SUMMARY = "summary"
    BEAT_BRIEF = "beat-brief"
    STORY_CANDIDATE = "story-candidate"
    TREND_NOTE = "trend-note"
    BUDGET_COMPARISON = "budget-comparison"
    POLICY_DIFF = "policy-diff"
    CONNECTION_MEMO = "connection-memo"
    CROSS_BEAT_FLAG = "cross-beat-flag"
    STORY_DRAFT = "story-draft"


class ProcessingProfile(StrEnum):
    """Downstream processing intent set at ingest time (spider or source default).

    Describes what the pipeline should produce after normalization.
    """

    FULL = "full"
    STRUCTURED = "structured"
    INDEX = "index"
    EVIDENCE = "evidence"


class SourceTier(StrEnum):
    """Whether a source is the issuing organization or a secondary reporter.

    PRIMARY: The originating organization itself — government portals, agency
        releases, court filings, official video streams. Default.
    SECONDARY: Another newsroom or analyst reporting on primary events —
        newspapers, wire services, think tanks. Requires ``outlet`` to be set
        on the Source row.
    """

    PRIMARY = "primary"
    SECONDARY = "secondary"


class SourceStatus(StrEnum):
    """Lifecycle flag for scheduled ingestion — inactive sources are skipped by list-due."""

    ACTIVE = "active"
    INACTIVE = "inactive"


GEO_TREE: dict[str, dict[str, dict[str, set[str]]]] = {
    "us": {
        "ca": {
            "tulare": {"visalia"},
            "san-bernardino": {"san-bernardino"},
            "shasta": {"redding"},
        },
        "il": {
            "springfield": {"springfield"},
        },
    },
}


BEAT_TREE: dict[str, dict[str, dict[str, set[str]]]] = {
    "government": {
        "city-council": {"budget": set()},
        "board-of-supervisors": {"budget": set()},
        "assessment-appeals-board": {},
        "pollution-control-board": {},
        "planning-commission": {},
    },
    "education": {
        "school-board": {"budget": set()},
    },
    "housing-zoning": {
        "zoning-board": {},
    },
    "public-safety": {
        "police-department": {},
    },
    "budget-finance": {
    },
}


def navigate_tree(
    tree: dict[str, dict[str, dict[str, set[str]]]],
    id: str,
    error_format: str = "colon-separated segments"
) -> list[str]:
    """Navigate a hierarchical tree structure using a colon-delimited identifier.

    Args:
        tree: Nested dict structure (up to 4 levels deep).
        id: Colon-delimited identifier (e.g., "a:b:c" or "a:b:c:d").
        error_format: Custom error message format hint for better error messages.

    Returns:
        List of validated path segments.

    Raises:
        ValueError: If the identifier is invalid or not found in the tree.
    """
    parts = id.split(":")
    if not parts or not parts[0]:
        raise ValueError(f"Invalid id {id!r}. Expected {error_format}.")

    # Handle up to 4 segments safely
    first = parts[0]
    second = parts[1] if len(parts) > 1 else None
    third = parts[2] if len(parts) > 2 else None
    fourth = parts[3] if len(parts) > 3 else None

    if len(parts) > 4:
        raise ValueError(
            f"Invalid id {id!r}. Too many segments. Expected {error_format}.")

    node = tree.get(first)
    if node is None:
        raise ValueError(
            f"Invalid id {id!r}. First segment {first!r} not found. Expected {error_format}.")
    if second is None:
        return [first]
    node = node.get(second)
    if node is None:
        raise ValueError(
            f"Invalid id {id!r}. Second segment {second!r} not found under {first!r}. Expected {error_format}.")
    if third is None:
        return [first, second]
    node = node.get(third)
    if node is None:
        raise ValueError(
            f"Invalid id {id!r}. Third segment {third!r} not found under {first!r}:{second!r}. Expected {error_format}.")
    if fourth is None:
        return [first, second, third]
    if fourth not in node:
        raise ValueError(
            f"Invalid id {id!r}. Fourth segment {fourth!r} not found under {first!r}:{second!r}:{third!r}. Expected {error_format}.")
    return [first, second, third, fourth]


def _identifier_core_schema(cls: type) -> CoreSchema:
    """Shared Pydantic v2 core schema for :class:`GeoIdentifier` / :class:`BeatIdentifier`."""

    def validate(value: Any) -> Any:
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(value)
        raise TypeError(f"Expected str or {cls.__name__}, got {type(value).__name__}")

    return core_schema.no_info_after_validator_function(
        validate,
        core_schema.union_schema(
            [
                core_schema.is_instance_schema(cls),
                core_schema.str_schema(),
            ]
        ),
        serialization=core_schema.plain_serializer_function_ser_schema(
            lambda instance: str(instance),
            return_schema=core_schema.str_schema(),
        ),
    )


def _identifier_json_schema(
    description: str,
    _core_schema: CoreSchema,
    handler: GetJsonSchemaHandler,
) -> JsonSchemaValue:
    json_schema = handler(core_schema.str_schema())
    if isinstance(json_schema, dict):
        json_schema = {**json_schema, "description": description}
    return json_schema


class GeoIdentifier:
    def __init__(self, geo_id: str):
        self.geo_id = geo_id
        self.parts = navigate_tree(
            GEO_TREE, geo_id, error_format="format: <country>:<state>:<county>:<city>")

    def __str__(self) -> str:
        return self.geo_id

    def __repr__(self) -> str:
        return f"GeoIdentifier({self.geo_id})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, GeoIdentifier):
            return self.geo_id == other.geo_id
        if isinstance(other, str):
            return self.geo_id == other
        return False

    def __hash__(self) -> int:
        return hash(self.geo_id)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source: Any, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return _identifier_core_schema(cls)

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema_obj: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return _identifier_json_schema(
            "Colon-delimited geo key validated against GEO_TREE "
            "(country:state:county:city).",
            core_schema_obj,
            handler,
        )


class BeatIdentifier:
    def __init__(self, beat_id: str):
        self.beat_id = beat_id
        self.parts = navigate_tree(
            BEAT_TREE, beat_id, error_format="format: <domain>:<subdomain>:<leaf>")

    def __str__(self) -> str:
        return self.beat_id

    def __repr__(self) -> str:
        return f"BeatIdentifier({self.beat_id})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BeatIdentifier):
            return self.beat_id == other.beat_id
        if isinstance(other, str):
            return self.beat_id == other
        return False

    def __hash__(self) -> int:
        return hash(self.beat_id)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source: Any, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return _identifier_core_schema(cls)

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        core_schema_obj: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return _identifier_json_schema(
            "Colon-delimited beat key validated against BEAT_TREE "
            "(domain:subdomain[:leaf]).",
            core_schema_obj,
            handler,
        )


def validate_beat(beat: str) -> str:
    """Validate a beat identifier and return the canonical string form.

    Constructs a BeatIdentifier to validate against BEAT_TREE, then returns
    the canonical string representation for serialization.

    Args:
        beat: Beat identifier string (colon-delimited format).

    Returns:
        The validated beat identifier string.

    Raises:
        ValueError: If the beat identifier is invalid.
    """
    identifier = BeatIdentifier(beat)
    return str(identifier)


def validate_geo(geo: str) -> str:
    """Validate a geo identifier and return the canonical string form.

    Constructs a GeoIdentifier to validate against GEO_TREE, then returns
    the canonical string representation for serialization.

    Args:
        geo: Geo identifier string (colon-delimited format).

    Returns:
        The validated geo identifier string.

    Raises:
        ValueError: If the geo identifier is invalid.
    """
    identifier = GeoIdentifier(geo)
    return str(identifier)
