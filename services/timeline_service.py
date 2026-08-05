# services/timeline/service.py
"""Chronological event timeline management."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from models.event_model import Event


EventPredicate = Callable[[Event], bool]


class TimelineService:
    """Store, query, and export Event objects in chronological order."""

    def __init__(self, events: Iterable[Event] | None = None) -> None:
        self._events: list[Event] = []
        if events is not None:
            for event in events:
                self.add_event(event)

    def add_event(self, event: Event) -> Event:
        """Add an event and keep the timeline ordered by timestamp."""
        if not isinstance(event, Event):
            raise TypeError("TimelineService accepts Event objects only.")

        self._events.append(event)
        self._events.sort(key=lambda item: item.timestamp)
        return event

    def get_events(self) -> list[Event]:
        """Return events in chronological order without exposing internal storage."""
        return list(self._events)

    def filter(
        self,
        predicate: EventPredicate | None = None,
        *,
        category: str | None = None,
        event: str | None = None,
        source: str | None = None,
        severity: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Event]:
        """Return matching events while preserving chronological order."""
        if predicate is not None and not callable(predicate):
            raise TypeError("predicate must be callable.")
        if start is not None and end is not None and start > end:
            raise ValueError("start must not be later than end.")

        def matches(candidate: Event) -> bool:
            return (
                (predicate is None or predicate(candidate))
                and (category is None or candidate.category == category)
                and (event is None or candidate.event == event)
                and (source is None or candidate.source == source)
                and (severity is None or candidate.severity == severity)
                and (start is None or candidate.timestamp >= start)
                and (end is None or candidate.timestamp <= end)
            )

        return [candidate for candidate in self._events if matches(candidate)]

    def export(self, file_path: str | Path | None = None) -> str:
        """Serialize the timeline to JSON and optionally write it to disk."""
        serialized = json.dumps(
            [event.to_dict() for event in self._events],
            ensure_ascii=False,
            indent=2,
        )
        if file_path is not None:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(serialized, encoding="utf-8")
        return serialized
