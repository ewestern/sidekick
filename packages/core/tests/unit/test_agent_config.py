"""Unit tests for AgentConfigRegistry.

All database calls are mocked — these tests run without any external services.
Covers: resolve(), set(), delete(), list(), cache behaviour.
"""

from time import monotonic
from unittest.mock import MagicMock, patch

import pytest

from sidekick.core.agent_config import AgentConfigRegistry, ResolvedAgentConfig
from sidekick.core.models import AgentConfig


def _registry() -> AgentConfigRegistry:
    return AgentConfigRegistry(db_url="postgresql://unused")


def _make_row(
    agent_id: str = "test-agent",
    model: str = "claude-sonnet-4-6",
    prompts: dict | None = None,
) -> AgentConfig:
    return AgentConfig(
        id="cfg_01",
        agent_id=agent_id,
        model=model,
        prompts=prompts or {"system": "You are a test agent."},
    )


def _patch_session(registry: AgentConfigRegistry, row: AgentConfig | None = None):
    """Patch Session so exec().first() returns row (or None)."""
    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: mock_session
    mock_session.__exit__ = MagicMock(return_value=False)
    exec_result = MagicMock()
    exec_result.first.return_value = row
    exec_result.all.return_value = [row] if row else []
    mock_session.exec = MagicMock(return_value=exec_result)
    mock_session.refresh = lambda obj: None
    return patch("sidekick.core.agent_config.Session", return_value=mock_session)


# ------------------------------------------------------------------
# resolve — happy path
# ------------------------------------------------------------------

def test_resolve_returns_config_when_exists():
    reg = _registry()
    row = _make_row(agent_id="ingestion-worker", model="claude-sonnet-4-6")
    with _patch_session(reg, row=row):
        result = reg.resolve("ingestion-worker")
    assert isinstance(result, ResolvedAgentConfig)
    assert result.agent_id == "ingestion-worker"
    assert result.model == "claude-sonnet-4-6"
    assert result.prompts == {"system": "You are a test agent."}


def test_resolve_raises_when_no_config_exists():
    reg = _registry()
    with _patch_session(reg, row=None):
        with pytest.raises(KeyError, match="ingestion-worker"):
            reg.resolve("ingestion-worker")


# ------------------------------------------------------------------
# resolve — cache behaviour
# ------------------------------------------------------------------

def test_resolve_caches_result():
    reg = _registry()
    row = _make_row()

    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: mock_session
    mock_session.__exit__ = MagicMock(return_value=False)
    exec_result = MagicMock()
    exec_result.first.return_value = row
    mock_session.exec = MagicMock(return_value=exec_result)

    with patch("sidekick.core.agent_config.Session", return_value=mock_session):
        reg.resolve("test-agent")
        reg.resolve("test-agent")

    # DB should only be queried once — second call hits cache
    assert mock_session.exec.call_count == 1


def test_resolve_bypasses_cache_after_ttl(monkeypatch):
    reg = _registry()
    row = _make_row()

    call_count = 0

    original_session = MagicMock()
    original_session.__enter__ = lambda s: original_session
    original_session.__exit__ = MagicMock(return_value=False)
    exec_result = MagicMock()
    exec_result.first.return_value = row
    original_session.exec = MagicMock(return_value=exec_result)
    original_session.refresh = lambda obj: None

    with patch("sidekick.core.agent_config.Session", return_value=original_session):
        reg.resolve("test-agent")

    # Expire the cache by backdating the timestamp
    cached, _ = reg._cache["test-agent"]
    reg._cache["test-agent"] = (cached, monotonic() - 120.0)

    with patch("sidekick.core.agent_config.Session", return_value=original_session):
        reg.resolve("test-agent")

    assert original_session.exec.call_count == 2


def test_resolve_cache_is_per_agent_id():
    reg = _registry()
    row_a = _make_row(agent_id="agent-a")
    row_b = _make_row(agent_id="agent-b", model="claude-opus-4-6")

    with _patch_session(reg, row=row_a):
        result_a = reg.resolve("agent-a")

    with _patch_session(reg, row=row_b):
        result_b = reg.resolve("agent-b")

    assert result_a.model == "claude-sonnet-4-6"
    assert result_b.model == "claude-opus-4-6"


# ------------------------------------------------------------------
# set
# ------------------------------------------------------------------

def test_set_creates_new_config():
    reg = _registry()
    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: mock_session
    mock_session.__exit__ = MagicMock(return_value=False)
    exec_result = MagicMock()
    exec_result.first.return_value = None  # no existing row
    mock_session.exec = MagicMock(return_value=exec_result)
    mock_session.refresh = lambda obj: None

    with patch("sidekick.core.agent_config.Session", return_value=mock_session):
        reg.set("new-agent", model="claude-sonnet-4-6", prompts={"system": "Hello"})

    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


def test_set_updates_existing_config():
    reg = _registry()
    existing = _make_row(model="claude-sonnet-4-6")

    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: mock_session
    mock_session.__exit__ = MagicMock(return_value=False)
    exec_result = MagicMock()
    exec_result.first.return_value = existing
    mock_session.exec = MagicMock(return_value=exec_result)
    mock_session.refresh = lambda obj: None

    with patch("sidekick.core.agent_config.Session", return_value=mock_session):
        reg.set("test-agent", model="claude-opus-4-6", prompts={"system": "Updated"})

    assert existing.model == "claude-opus-4-6"
    assert existing.prompts == {"system": "Updated"}


def test_set_invalidates_cache():
    reg = _registry()
    row = _make_row()

    # Populate cache
    with _patch_session(reg, row=row):
        reg.resolve("test-agent")
    assert "test-agent" in reg._cache

    # set() should clear the cache entry
    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: mock_session
    mock_session.__exit__ = MagicMock(return_value=False)
    exec_result = MagicMock()
    exec_result.first.return_value = row
    mock_session.exec = MagicMock(return_value=exec_result)
    mock_session.refresh = lambda obj: None

    with patch("sidekick.core.agent_config.Session", return_value=mock_session):
        reg.set("test-agent", model="claude-opus-4-6", prompts={})

    assert "test-agent" not in reg._cache


# ------------------------------------------------------------------
# delete
# ------------------------------------------------------------------

def test_delete_removes_config():
    reg = _registry()
    row = _make_row()

    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: mock_session
    mock_session.__exit__ = MagicMock(return_value=False)
    exec_result = MagicMock()
    exec_result.first.return_value = row
    mock_session.exec = MagicMock(return_value=exec_result)

    with patch("sidekick.core.agent_config.Session", return_value=mock_session):
        reg.delete("test-agent")

    mock_session.delete.assert_called_once_with(row)
    mock_session.commit.assert_called_once()


def test_delete_raises_for_missing():
    reg = _registry()
    with _patch_session(reg, row=None):
        with pytest.raises(KeyError, match="test-agent"):
            reg.delete("test-agent")


def test_delete_invalidates_cache():
    reg = _registry()
    row = _make_row()

    # Populate cache
    with _patch_session(reg, row=row):
        reg.resolve("test-agent")
    assert "test-agent" in reg._cache

    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: mock_session
    mock_session.__exit__ = MagicMock(return_value=False)
    exec_result = MagicMock()
    exec_result.first.return_value = row
    mock_session.exec = MagicMock(return_value=exec_result)

    with patch("sidekick.core.agent_config.Session", return_value=mock_session):
        reg.delete("test-agent")

    assert "test-agent" not in reg._cache


# ------------------------------------------------------------------
# list
# ------------------------------------------------------------------

def test_list_returns_all_configs():
    reg = _registry()
    rows = [_make_row("agent-a"), _make_row("agent-b")]

    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: mock_session
    mock_session.__exit__ = MagicMock(return_value=False)
    exec_result = MagicMock()
    exec_result.all.return_value = rows
    mock_session.exec = MagicMock(return_value=exec_result)

    with patch("sidekick.core.agent_config.Session", return_value=mock_session):
        result = reg.list()

    assert len(result) == 2


def test_list_returns_empty_when_no_configs():
    reg = _registry()

    mock_session = MagicMock()
    mock_session.__enter__ = lambda s: mock_session
    mock_session.__exit__ = MagicMock(return_value=False)
    exec_result = MagicMock()
    exec_result.all.return_value = []
    mock_session.exec = MagicMock(return_value=exec_result)

    with patch("sidekick.core.agent_config.Session", return_value=mock_session):
        result = reg.list()

    assert result == []
