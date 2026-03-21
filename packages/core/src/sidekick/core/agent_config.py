"""Agent configuration service — model and prompt management for all agents.

Agents call resolve() at the start of each run to get their current config.
A row must exist in agent_configs before an agent can be invoked; resolve()
raises KeyError if it doesn't. Seed rows via AgentConfigRegistry.set().

Results are cached with a 60-second TTL. Writes (set/delete) immediately
invalidate the local cache entry so the next resolve() re-fetches from DB.
"""

import logging
from datetime import UTC, datetime
from time import monotonic

import ulid
from pydantic import BaseModel
from sqlmodel import Session, create_engine, select

from sidekick.core.models import AgentConfig

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 60.0


class ResolvedAgentConfig(BaseModel):
    """Agent configuration value object passed to agent factories and nodes.

    Agents always receive this type — never the raw AgentConfig SQLModel.
    """

    agent_id: str
    model: str
    prompts: dict[str, str]  # slot_name -> prompt text


class AgentConfigRegistry:
    """CRUD interface for agent configurations.

    Agents call resolve() to get their current config. All writes invalidate
    the local TTL cache so changes propagate within one cache cycle (60s max).
    """

    def __init__(self, db_url: str) -> None:
        """
        Args:
            db_url: SQLAlchemy-compatible Postgres connection string.
        """
        self._engine = create_engine(db_url)
        self._cache: dict[str, tuple[ResolvedAgentConfig, float]] = {}

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def resolve(self, agent_id: str) -> ResolvedAgentConfig:
        """Return the resolved config for agent_id.

        Results are cached for up to 60 seconds. Writes via set() or delete()
        invalidate the cache entry immediately.

        Args:
            agent_id: Logical agent name (e.g. "ingestion-worker").

        Returns:
            ResolvedAgentConfig with model and prompts.

        Raises:
            KeyError: If no config row exists for agent_id. Seed one with set().
        """
        cached, ts = self._cache.get(agent_id, (None, 0.0))  # type: ignore[misc]
        if cached is not None and (monotonic() - ts) < _CACHE_TTL_SECONDS:
            return cached

        with Session(self._engine) as session:
            stmt = select(AgentConfig).where(AgentConfig.agent_id == agent_id)
            row = session.exec(stmt).first()

        if row is None:
            raise KeyError(
                f"No config found for agent {agent_id!r}. "
                "Seed a row with AgentConfigRegistry.set() before invoking this agent."
            )

        result = ResolvedAgentConfig(
            agent_id=row.agent_id,
            model=row.model,
            prompts=row.prompts,
        )
        self._cache[agent_id] = (result, monotonic())
        return result

    def list(self) -> list[AgentConfig]:
        """Return all agent config rows."""
        with Session(self._engine) as session:
            return list(session.exec(select(AgentConfig)).all())

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def set(
        self,
        agent_id: str,
        model: str,
        prompts: dict[str, str],
        updated_by: str | None = None,
    ) -> AgentConfig:
        """Create or update the config for agent_id.

        Upserts by agent_id. Invalidates the cache entry for this agent.

        Args:
            agent_id: Logical agent name.
            model: Model identifier (e.g. "claude-sonnet-4-6").
            prompts: Dict of slot_name -> prompt text.
            updated_by: Optional user ID for audit trail.

        Returns:
            The persisted AgentConfig row.
        """
        self._cache.pop(agent_id, None)
        now = datetime.now(UTC)

        with Session(self._engine) as session:
            stmt = select(AgentConfig).where(AgentConfig.agent_id == agent_id)
            row = session.exec(stmt).first()
            if row is None:
                row = AgentConfig(
                    id=f"cfg_{ulid.new()}",
                    agent_id=agent_id,
                    model=model,
                    prompts=prompts,
                    updated_at=now,
                    updated_by=updated_by,
                )
                session.add(row)
            else:
                row.model = model
                row.prompts = prompts
                row.updated_at = now
                row.updated_by = updated_by
                session.add(row)
            session.commit()
            session.refresh(row)

        logger.debug("Set config for agent %s (model=%s)", agent_id, model)
        return row

    def delete(self, agent_id: str) -> None:
        """Delete the config for agent_id. Invalidates the cache entry.

        Args:
            agent_id: Logical agent name.

        Raises:
            KeyError: If no config row exists for agent_id.
        """
        self._cache.pop(agent_id, None)

        with Session(self._engine) as session:
            stmt = select(AgentConfig).where(AgentConfig.agent_id == agent_id)
            row = session.exec(stmt).first()
            if row is None:
                raise KeyError(f"No config found for agent {agent_id!r}")
            session.delete(row)
            session.commit()

        logger.debug("Deleted config for agent %s", agent_id)
