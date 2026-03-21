"""Shared agent execution helpers."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)


@dataclass
class RunStats:
    """Accumulated token usage across an agent run."""

    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    tool_calls: list[str] = field(default_factory=list)

    @property
    def cache_hit_pct(self) -> float:
        cacheable = self.cache_creation_tokens + self.cache_read_tokens
        return (self.cache_read_tokens / cacheable * 100) if cacheable else 0.0

    def log_summary(self) -> None:
        logger.info(
            "[run total] calls=%d  in=%d  out=%d  "
            "cache_create=%d  cache_read=%d (%.0f%% hit rate)",
            self.llm_calls,
            self.input_tokens,
            self.output_tokens,
            self.cache_creation_tokens,
            self.cache_read_tokens,
            self.cache_hit_pct,
        )


def _extract_usage(msg: AIMessage) -> dict[str, int]:
    """Pull token usage from the standardized usage_metadata attribute."""
    um: dict = getattr(msg, "usage_metadata", None) or {}
    details: dict = um.get("input_token_details") or {}
    return {
        "input_tokens": int(um.get("input_tokens", 0)),
        "output_tokens": int(um.get("output_tokens", 0)),
        "cache_creation_tokens": int(details.get("cache_creation", 0)),
        "cache_read_tokens": int(details.get("cache_read", 0)),
    }


class UsageLoggingCallback(BaseCallbackHandler):
    """LangChain callback handler for per-call token usage and tool logs."""

    def __init__(self, verbose: bool = False) -> None:
        self._verbose = verbose
        self.stats = RunStats()

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Capture token usage from each generated AI message."""
        for generation_batch in response.generations:
            for generation in generation_batch:
                message = getattr(generation, "message", None)
                if not isinstance(message, AIMessage):
                    continue
                usage = _extract_usage(message)
                self.stats.llm_calls += 1
                self.stats.input_tokens += usage["input_tokens"]
                self.stats.output_tokens += usage["output_tokens"]
                self.stats.cache_creation_tokens += usage["cache_creation_tokens"]
                self.stats.cache_read_tokens += usage["cache_read_tokens"]
                if self._verbose:
                    logger.info(
                        "[llm #%d] in=%d  out=%d  cache_create=%d  cache_read=%d",
                        self.stats.llm_calls,
                        usage["input_tokens"],
                        usage["output_tokens"],
                        usage["cache_creation_tokens"],
                        usage["cache_read_tokens"],
                    )

    def on_tool_start(
        self, serialized: dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Log tool invocation previews."""
        if not self._verbose:
            return
        tool_name = serialized.get("name") or "tool"
        logger.info("  → %s(%s)", tool_name, input_str[:200])
        self.stats.tool_calls.append(tool_name)

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        """Log tool result previews."""
        if not self._verbose:
            return
        logger.info("  ← tool: %s", str(output)[:200])


def build_usage_logging_callbacks(verbose: bool) -> list[BaseCallbackHandler]:
    """Build callback list used by LLM invocations for usage logging."""
    if not verbose:
        return []
    return [UsageLoggingCallback(verbose=True)]
