"""Beat agent invocation scope — event-group or date-window."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class EventGroupScope:
    """Scope a beat agent run to a single event group (e.g. one council meeting)."""

    event_group: str


@dataclass(frozen=True)
class DateWindowScope:
    """Scope a beat agent run to a beat/geo date window (e.g. for assignments)."""

    since: date
    until: date


BeatScope = EventGroupScope | DateWindowScope
