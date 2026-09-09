from __future__ import annotations

"""Build reviewed Lokkestiiz raid-review windows from observed clock boundaries.

This adapter consumes semantic encounter-clock evidence that has already been tied to
canonical encounter facts. Numeric ESO ability IDs may be used upstream to discover
those boundaries, but are deliberately absent here.
"""

from dataclasses import dataclass
from typing import Iterable

from services.performance_raid_review_mechanic_window_service import (
    RaidReviewEncounterWindow,
)
from services.rotation_lokkestiiz_landing_clock_service import (
    EncounterObservedClockBoundary,
)


_CANONICAL_FLIGHT_FACT_KEY = "aerial_onslaught_flight"
_LOKKE_KEYS = {"lokkestiiz", "sunspire_lokkestiiz"}


@dataclass(frozen=True, slots=True)
class LokkestiizRaidReviewWindowResult:
    windows: tuple[RaidReviewEncounterWindow, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return not self.unresolved


class PerformanceRaidReviewLokkestiizWindowService:
    """Pair observed flight begin/end boundaries into reviewed coaching windows."""

    def build(
        self,
        *,
        report_code: str,
        fight_id: int,
        boundaries: Iterable[EncounterObservedClockBoundary],
    ) -> LokkestiizRaidReviewWindowResult:
        report_code = str(report_code or "").strip()
        if not report_code:
            raise ValueError("Lokkestiiz raid-review windows require report_code.")
        fight_id = int(fight_id)
        if fight_id <= 0:
            raise ValueError("Lokkestiiz raid-review windows require positive fight_id.")

        relevant = tuple(
            item
            for item in boundaries
            if item.encounter_id in _LOKKE_KEYS
            and item.fact_key == _CANONICAL_FLIGHT_FACT_KEY
            and item.boundary in {"begin", "start", "end"}
        )
        if not relevant:
            return LokkestiizRaidReviewWindowResult(
                windows=(),
                unresolved=(
                    "No observed Lokkestiiz aerial_onslaught_flight begin/end boundaries were supplied.",
                ),
            )

        by_occurrence: dict[int, dict[str, list[EncounterObservedClockBoundary]]] = {}
        for item in relevant:
            boundary = "begin" if item.boundary in {"begin", "start"} else "end"
            by_occurrence.setdefault(item.occurrence, {}).setdefault(boundary, []).append(item)

        windows: list[RaidReviewEncounterWindow] = []
        unresolved: list[str] = []
        for occurrence in sorted(by_occurrence):
            bucket = by_occurrence[occurrence]
            starts = sorted(bucket.get("begin", ()), key=lambda item: item.time_seconds)
            ends = sorted(bucket.get("end", ()), key=lambda item: item.time_seconds)

            if len(starts) != 1 or len(ends) != 1:
                unresolved.append(
                    "Lokkestiiz flight occurrence "
                    f"{occurrence} requires exactly one observed begin and one observed end boundary; "
                    f"begin={len(starts)}, end={len(ends)}."
                )
                continue

            start = starts[0]
            end = ends[0]
            if end.time_seconds <= start.time_seconds:
                unresolved.append(
                    f"Lokkestiiz flight occurrence {occurrence} ends at or before it begins."
                )
                continue

            sources = tuple(dict.fromkeys((start.source, end.source)))
            windows.append(
                RaidReviewEncounterWindow(
                    report_code=report_code,
                    fight_id=fight_id,
                    semantic_key=f"aerial_onslaught_flight_{occurrence}",
                    label=f"Aerial Onslaught Flight {occurrence}",
                    start_seconds=start.time_seconds,
                    end_seconds=end.time_seconds,
                    evidence_source="; ".join(sources),
                    reviewed=True,
                )
            )

        return LokkestiizRaidReviewWindowResult(
            windows=tuple(windows),
            unresolved=tuple(unresolved),
        )


__all__ = [
    "LokkestiizRaidReviewWindowResult",
    "PerformanceRaidReviewLokkestiizWindowService",
]
