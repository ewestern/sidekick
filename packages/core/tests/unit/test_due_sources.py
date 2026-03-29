"""Unit tests for due source listing (DB-driven, no spider discovery)."""

from unittest.mock import MagicMock

from sidekick.core.due_sources import list_due_source_ids, list_due_spiders_payload
from sidekick.core.models import Source


def test_list_due_source_ids_maps_registry_order():
    registry = MagicMock()
    registry.get_due_sources.return_value = [
        Source(id="a", name="A"),
        Source(id="b", name="B"),
    ]
    assert list_due_source_ids(registry) == ["a", "b"]


def test_list_due_spiders_payload_shape():
    registry = MagicMock()
    registry.get_due_sources.return_value = [Source(id="x", name="X")]
    assert list_due_spiders_payload(registry) == {"spiders": ["x"]}
