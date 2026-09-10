from __future__ import annotations

"""Build all reviewed Lokkestiiz raid-review evidence for one pull.

This service is the encounter-specific bridge between raw ESO Logs events and the
generic raid-review engine. It derives observed flight boundaries, converts complete
flight pairs into reviewed semantic mechanic windows, and measures each reviewed
post-landing recovery obligation independently.

Numeric ESO ability IDs remain confined to the boundary detector as raw evidence.
"""

from dataclasses import dataclass
from typing import Iterable

from services.performance_raid_review_landing_recovery_service import (
    RaidReviewLandingRecoveryObservation,
    RaidReviewRecoveryActor,
)
from services.performance_raid_review_lokkestiiz_boundary_service import (
    PerformanceRaidReviewLokkestiizBoundaryService,
)
from services.performance_raid_review_lokkestiiz_recovery_obligation_service import (
    PerformanceRaidReviewLokkestiizRecoveryObligationService,
)
from services.performance_raid_review_lokkestiiz_window_service import (
    PerformanceRaidReviewLokkestiizWindowService,
)
from services.performance_raid_review_mechanic_window_service import RaidReviewEncounterWindow
from services.rotation_lokkestiiz_landing_clock_service import EncounterObservedClockBoundary


@dataclass(frozen=True, slots=True)
class LokkestiizPullRaidReviewEvidence:
    boundaries: tuple[EncounterObservedClockBoundary, ...]
    mechanic_windows: tuple[RaidReviewEncounterWindow, ...]
    recovery_observations: tuple[RaidReviewLandingRecoveryObservation, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return not self.unresolved


class PerformanceRaidReviewLokkestiizPullService:
    """Produce reviewed raid-review evidence for one explicit Lokkestiiz pull."""

    def __init__(
        self,
        *,
        boundary_service: PerformanceRaidReviewLokkestiizBoundaryService | None = None,
        window_service: PerformanceRaidReviewLokkestiizWindowService | None = None,
        recovery_service: PerformanceRaidReviewLokkestiizRecoveryObligationService | None = None,
    ) -> None:
        self.boundary_service = boundary_service or PerformanceRaidReviewLokkestiizBoundaryService()
        self.window_service = window_service or PerformanceRaidReviewLokkestiizWindowService()
        self.recovery_service = recovery_service or PerformanceRaidReviewLokkestiizRecoveryObligationService()

    def build(
        self,
        *,
        report_code: str,
        fight_id: int,
        fight_start_time_ms: float,
        events: Iterable[dict],
        boss_actor_id: int,
        actors: Iterable[RaidReviewRecoveryActor],
        evidence_source: str,
        max_recovery_delay_seconds: float = 15.0,
    ) -> LokkestiizPullRaidReviewEvidence:
        rows = tuple(event for event in events if isinstance(event, dict))
        actor_rows = tuple(actors)
        unresolved: list[str] = []

        boundary_result = self.boundary_service.extract(
            rows,
            boss_actor_id=int(boss_actor_id),
            fight_start_time_ms=float(fight_start_time_ms),
            evidence_source=evidence_source,
        )
        unresolved.extend(boundary_result.unresolved)

        window_result = self.window_service.build(
            report_code=report_code,
            fight_id=int(fight_id),
            boundaries=boundary_result.boundaries,
        )
        unresolved.extend(window_result.unresolved)

        landing_boundaries = tuple(
            boundary
            for boundary in boundary_result.boundaries
            if boundary.fact_key == "aerial_onslaught_flight" and boundary.boundary == "end"
        )
        recovery_observations: tuple[RaidReviewLandingRecoveryObservation, ...] = ()
        if landing_boundaries and actor_rows:
            recovery_result = self.recovery_service.measure(
                report_code=report_code,
                fight_id=int(fight_id),
                fight_start_time_ms=float(fight_start_time_ms),
                events=rows,
                landing_boundaries=landing_boundaries,
                actors=actor_rows,
                boss_actor_id=int(boss_actor_id),
                max_delay_seconds=float(max_recovery_delay_seconds),
            )
            recovery_observations = recovery_result.observations
            unresolved.extend(recovery_result.unresolved)
        elif landing_boundaries and not actor_rows:
            unresolved.append("No raid actors were supplied for Lokkestiiz landing-recovery evidence.")

        return LokkestiizPullRaidReviewEvidence(
            boundaries=boundary_result.boundaries,
            mechanic_windows=window_result.windows,
            recovery_observations=recovery_observations,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "LokkestiizPullRaidReviewEvidence",
    "PerformanceRaidReviewLokkestiizPullService",
]
