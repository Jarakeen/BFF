from __future__ import annotations

"""Derive semantic Lokkestiiz flight boundaries from reviewed ESO Logs signatures.

The numeric ability IDs in this module are evidence signatures only. They are never
returned as canonical mechanic identity. Flight end is resolved from the first boss
damage event after the long observed airborne gap, not from the later confirmation
cast.
"""

from dataclasses import dataclass
from typing import Iterable

from services.rotation_lokkestiiz_landing_clock_service import (
    EncounterObservedClockBoundary,
)


# Reviewed against the current Lokkestiiz corpus. These are raw ESO Logs signatures,
# not stable semantic skill/mechanic IDs.
_REVIEWED_FLIGHT_ENTRY_SIGNATURES: dict[int, int] = {
    122820: 1,
    122821: 2,
    122822: 3,
}
_CANONICAL_FLIGHT_FACT_KEY = "aerial_onslaught_flight"
_DAMAGE_TYPES = {"damage", "calculateddamage"}
_CAST_TYPES = {"cast"}


@dataclass(frozen=True, slots=True)
class LokkestiizBoundaryExtractionResult:
    boundaries: tuple[EncounterObservedClockBoundary, ...]
    unresolved: tuple[str, ...] = ()


class PerformanceRaidReviewLokkestiizBoundaryService:
    """Resolve observed flight begin/end boundaries without HP->time inference."""

    def __init__(self, *, minimum_qualifying_damage_gap_seconds: float = 30.0) -> None:
        gap = float(minimum_qualifying_damage_gap_seconds)
        if gap <= 0:
            raise ValueError("minimum_qualifying_damage_gap_seconds must be positive")
        # The reviewed corpus showed completed flight gaps above ~51 seconds. This
        # threshold is a detector guard below that observed minimum, not encounter truth.
        self.minimum_qualifying_damage_gap_seconds = gap

    def extract(
        self,
        events: Iterable[dict],
        *,
        boss_actor_id: int,
        fight_start_time_ms: float,
        evidence_source: str,
    ) -> LokkestiizBoundaryExtractionResult:
        rows = tuple(
            sorted(
                (event for event in events if isinstance(event, dict)),
                key=self._timestamp,
            )
        )
        boss_actor_id = int(boss_actor_id)
        start_ms = float(fight_start_time_ms)
        source = str(evidence_source or "").strip()
        if not source:
            raise ValueError("Lokkestiiz boundary extraction requires evidence_source")

        entries: dict[int, dict] = {}
        duplicates: set[int] = set()
        for event in rows:
            if self._event_type(event) not in _CAST_TYPES:
                continue
            ability_id = self._ability_game_id(event)
            occurrence = _REVIEWED_FLIGHT_ENTRY_SIGNATURES.get(ability_id)
            if occurrence is None:
                continue
            if occurrence in entries:
                duplicates.add(occurrence)
                continue
            entries[occurrence] = event

        boundaries: list[EncounterObservedClockBoundary] = []
        unresolved: list[str] = []
        for occurrence in sorted(entries):
            if occurrence in duplicates:
                unresolved.append(
                    f"Multiple reviewed Lokkestiiz flight-entry signatures were observed for occurrence {occurrence}; boundary was not selected."
                )
                continue

            entry = entries[occurrence]
            entry_ms = self._timestamp(entry)
            begin_seconds = max(0.0, (entry_ms - start_ms) / 1000.0)
            boundaries.append(
                EncounterObservedClockBoundary(
                    encounter_id="lokkestiiz",
                    fact_key=_CANONICAL_FLIGHT_FACT_KEY,
                    boundary="begin",
                    occurrence=occurrence,
                    time_seconds=begin_seconds,
                    source=(
                        f"{source}; reviewed ESO Logs flight-entry evidence signature"
                    ),
                )
            )

            next_entry_ms = self._next_entry_time(entries, occurrence)
            damage_events = [
                event
                for event in rows
                if self._event_type(event) in _DAMAGE_TYPES
                and self._int_or_none(event.get("targetID")) == boss_actor_id
                and self._positive_amount(event)
                and self._timestamp(event) >= entry_ms
                and (next_entry_ms is None or self._timestamp(event) < next_entry_ms)
            ]

            landing_ms = self._first_damage_after_qualifying_gap(damage_events)
            if landing_ms is None:
                unresolved.append(
                    f"No qualifying boss-damage resumption was observed after Lokkestiiz flight occurrence {occurrence}."
                )
                continue

            boundaries.append(
                EncounterObservedClockBoundary(
                    encounter_id="lokkestiiz",
                    fact_key=_CANONICAL_FLIGHT_FACT_KEY,
                    boundary="end",
                    occurrence=occurrence,
                    time_seconds=max(0.0, (landing_ms - start_ms) / 1000.0),
                    source=(
                        f"{source}; first positive boss damage after reviewed airborne-gap detector"
                    ),
                )
            )

        if not entries:
            unresolved.append("No reviewed Lokkestiiz flight-entry evidence signatures were observed.")

        return LokkestiizBoundaryExtractionResult(
            boundaries=tuple(boundaries),
            unresolved=tuple(unresolved),
        )

    def _first_damage_after_qualifying_gap(self, damage_events: list[dict]) -> float | None:
        if len(damage_events) < 2:
            return None
        threshold_ms = self.minimum_qualifying_damage_gap_seconds * 1000.0
        previous = self._timestamp(damage_events[0])
        for event in damage_events[1:]:
            current = self._timestamp(event)
            if current - previous >= threshold_ms:
                return current
            previous = current
        return None

    @staticmethod
    def _next_entry_time(entries: dict[int, dict], occurrence: int) -> float | None:
        later = [
            PerformanceRaidReviewLokkestiizBoundaryService._timestamp(event)
            for index, event in entries.items()
            if index > occurrence
        ]
        return min(later) if later else None

    @staticmethod
    def _event_type(event: dict) -> str:
        return str(event.get("type") or "").strip().casefold()

    @staticmethod
    def _timestamp(event: dict) -> float:
        try:
            return float(event.get("timestamp", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _int_or_none(value) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _ability_game_id(event: dict) -> int | None:
        for key in ("abilityGameID", "abilityGameId", "abilityID", "abilityId"):
            value = event.get(key)
            parsed = PerformanceRaidReviewLokkestiizBoundaryService._int_or_none(value)
            if parsed is not None:
                return parsed
        ability = event.get("ability")
        if isinstance(ability, dict):
            for key in ("gameID", "gameId", "id"):
                parsed = PerformanceRaidReviewLokkestiizBoundaryService._int_or_none(
                    ability.get(key)
                )
                if parsed is not None:
                    return parsed
        return None

    @staticmethod
    def _positive_amount(event: dict) -> bool:
        try:
            return float(event.get("amount", 0.0) or 0.0) > 0
        except (TypeError, ValueError):
            return False


__all__ = [
    "LokkestiizBoundaryExtractionResult",
    "PerformanceRaidReviewLokkestiizBoundaryService",
]
