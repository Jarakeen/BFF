# services/statistics_engine.py
"""Raid timeline statistics and JSON export."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from models.event_model import Event


class StatisticsEngine:
    """Compute pull, wipe, clear, duration, and success statistics."""

    def calculate(self, events: Iterable[Event]) -> dict[str, Any]:
        """Return statistics for a chronological collection of Event objects."""
        timeline = self._ordered_events(events)
        pulls = [event for event in timeline if self._is_pull_start(event)]
        wipes = [event for event in timeline if self._is_wipe(event)]
        clears = [event for event in timeline if self._is_clear(event)]
        durations = self._pull_durations(timeline)
        clear_durations = [duration for duration, outcome in durations if outcome == "clear"]
        duration_values = [duration for duration, _ in durations]
        total_pulls = len(pulls)
        total_clears = len(clears)
        total_wipes = len(wipes)

        return {
            "total_pulls": total_pulls,
            "total_wipes": total_wipes,
            "total_clears": total_clears,
            "average_pull_length": self._average(duration_values),
            "fastest_clear": min(clear_durations) if clear_durations else None,
            "longest_pull": max(duration_values) if duration_values else None,
            "success_rate": round((total_clears / total_pulls) * 100, 2) if total_pulls else 0.0,
        }

    def export(
        self,
        events: Iterable[Event],
        file_path: str | Path | None = None,
    ) -> str:
        """Serialize calculated statistics to JSON and optionally write them."""
        serialized = json.dumps(self.calculate(events), ensure_ascii=False, indent=2)
        if file_path is not None:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(serialized, encoding="utf-8")
        return serialized

    @staticmethod
    def _ordered_events(events: Iterable[Event]) -> list[Event]:
        timeline = list(events)
        if any(not isinstance(event, Event) for event in timeline):
            raise TypeError("StatisticsEngine accepts Event objects only.")
        return sorted(timeline, key=lambda event: event.timestamp)

    @staticmethod
    def _is_pull_start(event: Event) -> bool:
        label = StatisticsEngine._label(event)
        return label in {"pull", "pull started", "pull start", "trial pull"}

    @staticmethod
    def _is_wipe(event: Event) -> bool:
        return "wipe" in StatisticsEngine._label(event) or "failed" in StatisticsEngine._label(event)

    @staticmethod
    def _is_clear(event: Event) -> bool:
        label = StatisticsEngine._label(event)
        return "clear" in label or "victory" in label or "boss defeated" in label

    @staticmethod
    def _label(event: Event) -> str:
        return re.sub(r"\s+", " ", event.event.strip().lower().replace("_", " "))

    @staticmethod
    def _duration_from_payload(event: Event) -> float | None:
        for key in ("duration_seconds", "pull_length_seconds", "duration", "length_seconds"):
            value = event.payload.get(key)
            if isinstance(value, (int, float)) and value >= 0:
                return float(value)
        return None

    def _pull_durations(self, events: list[Event]) -> list[tuple[float, str | None]]:
        durations: list[tuple[float, str | None]] = []
        active_pull: Event | None = None

        for event in events:
            if self._is_pull_start(event):
                if active_pull is not None:
                    duration = self._duration_between(active_pull, event)
                    if duration is not None:
                        durations.append((duration, None))
                active_pull = event
                continue

            if active_pull is None or not (self._is_wipe(event) or self._is_clear(event)):
                continue

            duration = self._duration_from_payload(event) or self._duration_between(active_pull, event)
            if duration is not None:
                durations.append((duration, "clear" if self._is_clear(event) else "wipe"))
            active_pull = None

        return durations

    @staticmethod
    def _duration_between(start: Event, end: Event) -> float | None:
        duration = (end.timestamp - start.timestamp).total_seconds()
        return duration if duration >= 0 else None

    @staticmethod
    def _average(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 2) if values else None
