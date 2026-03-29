"""Unit tests for SourceRegistry.

All database calls are mocked — these tests run without any external services.
They cover: CRUD operations, get_due_sources schedule evaluation, update_health merge behavior.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from sidekick.core.models import Source
from sidekick.core.vocabulary import SourceStatus
from sidekick.registry.registry import SourceRegistry


def _registry() -> SourceRegistry:
    return SourceRegistry(db_url="postgresql://unused")


def _patch_session(registry: SourceRegistry, stored: dict | None = None):
    """Patch Session to avoid real DB calls. stored maps source_id -> Source."""
    stored = stored or {}
    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: mock_session
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.get = lambda model, pk: stored.get(pk)
    exec_result = MagicMock()
    exec_result.all.return_value = list(stored.values())
    mock_session.exec = MagicMock(return_value=exec_result)
    return patch("sidekick.registry.registry.Session", return_value=mock_session)


def _make_source(
    source_id: str = "src_test",
    schedule: dict | None = None,
    health: dict | None = None,
    **kwargs,
) -> Source:
    return Source(
        id=source_id,
        name="Test Source",
        schedule=schedule,
        health=health,
        **kwargs,
    )


# ------------------------------------------------------------------
# get
# ------------------------------------------------------------------

def test_get_returns_source():
    reg = _registry()
    src = _make_source("src_1")
    with _patch_session(reg, stored={"src_1": src}):
        result = reg.get("src_1")
    assert result.id == "src_1"


def test_get_missing_raises():
    reg = _registry()
    with _patch_session(reg, stored={}):
        with pytest.raises(KeyError):
            reg.get("does_not_exist")


# ------------------------------------------------------------------
# list
# ------------------------------------------------------------------

def test_list_unsupported_filter_raises():
    reg = _registry()
    with pytest.raises(ValueError, match="Unsupported filter key"):
        reg.list(filters={"nonexistent": "value"})


def test_list_returns_all_when_no_filters():
    reg = _registry()
    sources = {"src_a": _make_source("src_a"), "src_b": _make_source("src_b")}
    with _patch_session(reg, stored=sources):
        results = reg.list()
    assert len(results) == 2



# ------------------------------------------------------------------
# create
# ------------------------------------------------------------------

def test_create_raises_if_source_exists():
    reg = _registry()
    src = _make_source("src_dup")
    with _patch_session(reg, stored={"src_dup": src}):
        with pytest.raises(ValueError, match="already exists"):
            reg.create(src)


def test_create_persists_new_source():
    reg = _registry()
    src = _make_source("src_new")
    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: mock_session
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.get = lambda model, pk: None  # does not exist
    mock_session.refresh = lambda obj: None
    with patch("sidekick.registry.registry.Session", return_value=mock_session):
        result = reg.create(src)
    mock_session.add.assert_called_once_with(src)
    mock_session.commit.assert_called_once()


# ------------------------------------------------------------------
# update_health — merge behavior
# ------------------------------------------------------------------

def test_update_health_merges_fields():
    reg = _registry()
    src = _make_source(
        "src_h", health={"status": "active", "last_checked": "2026-01-01T00:00:00Z"})
    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: mock_session
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.get = lambda model, pk: src

    with patch("sidekick.registry.registry.Session", return_value=mock_session):
        reg.update_health(
            "src_h", {"last_checked": "2026-03-18T08:00:00Z", "error_rate_30d": 0.01})

    # Health should be merged, not replaced
    assert src.health is not None
    assert src.health["status"] == "active"  # existing field preserved
    assert src.health["last_checked"] == "2026-03-18T08:00:00Z"  # updated
    assert src.health["error_rate_30d"] == 0.01  # new field added


def test_update_health_raises_for_missing_source():
    reg = _registry()
    with _patch_session(reg, stored={}):
        with pytest.raises(KeyError):
            reg.update_health("missing_src", {"status": "active"})


# ------------------------------------------------------------------
# get_due_sources — schedule evaluation
# ------------------------------------------------------------------

def test_never_checked_source_is_always_due():
    """A source with a cron schedule but no last_checked is always due."""
    reg = _registry()
    src = _make_source(
        "src_never",
        schedule={"type": "cron", "expr": "0 8 * * MON"},
        
    )
    with patch.object(reg, "list", return_value=[src]):
        due = reg.get_due_sources()
    assert any(s.id == "src_never" for s in due)


def test_source_due_when_next_run_has_passed():
    """Source is due if the next scheduled time after last_checked is in the past."""
    reg = _registry()
    two_weeks_ago = (datetime.now(UTC) - timedelta(weeks=2)).isoformat()
    src = _make_source(
        "src_overdue",
        schedule={"type": "cron", "expr": "0 8 * * MON"},
        health={"last_checked": two_weeks_ago},
        
    )
    with patch.object(reg, "list", return_value=[src]):
        due = reg.get_due_sources()
    assert any(s.id == "src_overdue" for s in due)


def test_source_not_due_when_next_run_is_in_future():
    """Source is not due if it was just checked and next run is in the future."""
    reg = _registry()
    just_now = datetime.now(UTC).isoformat()
    src = _make_source(
        "src_fresh",
        schedule={"type": "cron", "expr": "0 8 * * MON"},
        health={"last_checked": just_now},
        
    )
    with patch.object(reg, "list", return_value=[src]):
        due = reg.get_due_sources()
    assert not any(s.id == "src_fresh" for s in due)


def test_non_cron_source_excluded():
    """Sources without a cron schedule are not returned by get_due_sources."""
    reg = _registry()
    src = _make_source(
        "src_reactive",
        schedule={"type": "reactive"},
        
    )
    with patch.object(reg, "list", return_value=[src]):
        due = reg.get_due_sources()
    assert len(due) == 0


def test_source_with_no_schedule_excluded():
    """Sources with no schedule are not returned by get_due_sources."""
    reg = _registry()
    src = _make_source("src_no_sched", schedule=None)
    with patch.object(reg, "list", return_value=[src]):
        due = reg.get_due_sources()
    assert len(due) == 0


def test_inactive_source_excluded_from_due():
    """Inactive sources are not returned by get_due_sources even when cron is due."""
    reg = _registry()
    src = _make_source(
        "src_inactive",
        schedule={"type": "cron", "expr": "0 8 * * MON"},
        status=SourceStatus.INACTIVE,
    )
    with patch.object(reg, "list", return_value=[src]):
        due = reg.get_due_sources()
    assert len(due) == 0
