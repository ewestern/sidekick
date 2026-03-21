"""Upsert default agent_configs rows. Idempotent."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from sidekick.core.agent_config import AgentConfigRegistry

load_dotenv()

# ── Base class source (included verbatim in the prompt) ───────────────────────



DEFAULT_MODEL = "openai:gpt-5.4-mini"


def seed(db_url: str | None = None) -> None:
    """Upsert agent_configs rows for unsupervised pipeline agents.

    The source-examination agent is run interactively by developers and is
    configured inline in examination.py — it does not need a DB row.
    """
    # Nothing to seed yet — future agents (beat, editor, etc.) go here.
    _ = db_url  # reserved for when rows are added


def main() -> None:
    seed()
    print("Seeded agent_configs (nothing to seed yet).")


if __name__ == "__main__":
    main()
