from __future__ import annotations

from dataclasses import dataclass
import math

from services.rotation_lokkestiiz_healer_scenario import LokkestiizHealerScenario


_CANONICAL_FLIGHT_FACT_KEY = "aerial_onslaught_flight"


@dataclass(frozen=True)
class EncounterObservedClockBoundary:
    """One observed clock boundary tied to an existing canonical encounter fact.

    The clock is pull/runtime evidence. It does not replace canonical encounter
    truth and must not be inferred from health thresholds or prose strategy.
    """

    encounter_id: str
    fact_key: str
    boundary: str
    occurrence: int
    time_seconds: float
    source: str

    def __post_init__(self) -> None:
        encounter_id = str(self.encounter_id or "").strip().casefold()
        fact_key = str(self.fact_key or "").strip().casefold()
        boundary = str(self.boundary or "").strip().casefold()
        source = str(self.source or "").strip()
        occurrence = int(self.occurrence)
        time_seconds = float(self.time_seconds)
        if not encounter_id or not fact_key or not boundary or not source:
            raise ValueError("observed encounter clock boundary requires encounter, fact, boundary, and source")
        if occurrence <= 0:
            raise ValueError("observed encounter clock occurrence must be positive")
        if not math.isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("observed encounter clock time must be finite and non-negative")
        object.__setattr__(self, "encounter_id", encounter_id)
        object.__setattr__(self, "fact_key", fact_key)
        object.__setattr__(self, "boundary", boundary)
        object.__setattr__(self, "occurrence", occurrence)
        object.__setattr__(self, "time_seconds", time_seconds)
        object.__setattr__(self, "source", source)


@dataclass(frozen=True)
class LokkestiizLandingClockEvidence:
    landing_times_seconds: tuple[float, ...]
    sources: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return not self.unresolved


class RotationLokkestiizLandingClockService:
    """Resolve observed Lokkestiiz landing clocks without converting HP to time."""

    def resolve(
        self,
        *,
        scenario: LokkestiizHealerScenario,
        boundaries: tuple[EncounterObservedClockBoundary, ...],
    ) -> LokkestiizLandingClockEvidence:
        encounter_id = scenario.execution.encounter_id.casefold()
        matches = tuple(
            item
            for item in boundaries
            if item.encounter_id == encounter_id
            and item.fact_key == _CANONICAL_FLIGHT_FACT_KEY
            and item.boundary == "end"
        )
        ordered = tuple(sorted(matches, key=lambda item: (item.occurrence, item.time_seconds)))
        unresolved: list[str] = []

        expected = scenario.execution.requested_cycles
        if len(ordered) != expected:
            unresolved.append(
                "observed Lokkestiiz landing clocks do not match requested execution cycles: "
                f"observed={len(ordered)}, requested={expected}"
            )

        occurrences = tuple(item.occurrence for item in ordered)
        expected_occurrences = tuple(range(1, len(ordered) + 1))
        if occurrences != expected_occurrences:
            unresolved.append(
                "observed Lokkestiiz landing clock occurrences must be contiguous from 1: "
                f"observed={occurrences}"
            )

        times = tuple(item.time_seconds for item in ordered)
        if any(later <= earlier for earlier, later in zip(times, times[1:])):
            unresolved.append("observed Lokkestiiz landing clocks must be strictly increasing")

        return LokkestiizLandingClockEvidence(
            landing_times_seconds=times,
            sources=tuple(item.source for item in ordered),
            unresolved=tuple(unresolved),
        )


__all__ = [
    "EncounterObservedClockBoundary",
    "LokkestiizLandingClockEvidence",
    "RotationLokkestiizLandingClockService",
]
