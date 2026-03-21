"""Shared agent tools (HTTP, etc.). See docs/AGENT_DESIGN_PATTERNS.md."""

from sidekick.agents.tools.http import FetchResult, fetch_url

__all__ = ["FetchResult", "fetch_url"]
