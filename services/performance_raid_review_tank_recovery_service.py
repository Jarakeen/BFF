from __future__ import annotations

"""Measure explicit reviewed tank obligations after encounter recovery boundaries.

This is an interpretation adapter over the shared landing-recovery service. It owns no
ESO mechanics and does not assume one universal tank skill. Callers supply reviewed
semantic signals that match the tank's actual encounter assignment. Each signal is
measured independently so an early control action cannot hide a later support/debuff
obligation.
"""

from dataclasses import dataclass
from typing import Iterable

from services.performance_raid_review_landing_recovery_completion_analysis_service import (
    RaidReviewRecoveryOpportunity,
)
from services.performance_raid_review_landing_recovery_service import (
    PerformanceRaidReviewLandingRecoveryService,
    RaidReviewLandingRecoveryObservation,
    RaidReviewRecoveryActor,
    RaidReviewRecoverySignal,
)
from services.rotation_lokkestiiz_landing_clock_service import EncounterObservedClockBoundary


@dataclass(frozen=True, slots=True)
class RaidReviewTankRecoveryResult:
    observations: tuple[RaidReviewLandingRecoveryObservation, ...]
    opportunities: tuple[RaidReviewRecoveryOpportunity, ...]
    unresolved: tuple[str, ...] = ()


class PerformanceRaidReviewTankRecoveryService:
    """Measure caller-reviewed tank recovery obligations independently."""

    def __init__(
        self,
        *,
        recovery_service: PerformanceRaidReviewLandingRecoveryService | None = None,
    ) -> None:
        self.recovery_service = recovery_service or PerformanceRaidReviewLandingRecoveryService()

    def measure(
        self,
        *,
        report_code: str,
        fight_id: int,
        fight_start_time_ms: float,
        events: Iterable[dict],
        landing_boundaries: Iterable[EncounterObservedClockBoundary],
        actors: Iterable[RaidReviewRecoveryActor],
        signals: Iterable[RaidReviewRecoverySignal],
        boss_actor_id: int | None,
        max_delay_seconds: float = 15.0,
    ) -> RaidReviewTankRecoveryResult:
        rows = tuple(event for event in events if isinstance(event, dict))
        boundaries = tuple(
            boundary
            for boundary in landing_boundaries
            if boundary.fact_key == "aerial_onslaught_flight" and boundary.boundary == "end"
        )
        tank_actors = tuple(
            actor for actor in actors if self._canonical_role(actor.role) == "Tank"
        )
        reviewed_signals = tuple(
            signal
            for signal in signals
            if signal.reviewed and self._canonical_role(signal.role) == "Tank"
        )

        unresolved: list[str] = []
        observations: list[RaidReviewLandingRecoveryObservation] = []
        opportunities: list[RaidReviewRecoveryOpportunity] = []

        if not boundaries:
            return RaidReviewTankRecoveryResult(
                observations=(),
                opportunities=(),
                unresolved=("No observed landing boundaries were supplied for tank recovery.",),
            )
        if not tank_actors:
            return RaidReviewTankRecoveryResult(
                observations=(),
                opportunities=(),
                unresolved=("No Tank actors were supplied for tank recovery.",),
            )
        if not reviewed_signals:
            return RaidReviewTankRecoveryResult(
                observations=(),
                opportunities=(),
                unresolved=("No reviewed Tank recovery signals were supplied.",),
            )

        for actor in tank_actors:
            for signal in reviewed_signals:
                for boundary in boundaries:
                    opportunities.append(
                        RaidReviewRecoveryOpportunity(
                            report_code=str(report_code),
                            fight_id=int(fight_id),
                            occurrence=int(boundary.occurrence),
                            actor_id=int(actor.actor_id),
                            actor_label=str(actor.actor_label),
                            role="Tank",
                            member_key=str(actor.member_key or ""),
                            signal_semantic_key=str(signal.semantic_key),
                            signal_label=str(signal.label or signal.semantic_key),
                        )
                    )

                result = self.recovery_service.measure(
                    report_code=str(report_code),
                    fight_id=int(fight_id),
                    fight_start_time_ms=float(fight_start_time_ms),
                    events=rows,
                    landing_boundaries=boundaries,
                    actors=(actor,),
                    signals=(signal,),
                    boss_actor_id=boss_actor_id,
                    max_delay_seconds=float(max_delay_seconds),
                )
                observations.extend(result.observations)
                label = str(signal.label or signal.semantic_key)
                unresolved.extend(
                    f"{label} for {actor.actor_label}: {message}"
                    for message in result.unresolved
                )

        observations.sort(
            key=lambda row: (
                row.occurrence,
                row.actor_label.casefold(),
                row.signal_semantic_key,
            )
        )
        opportunities.sort(
            key=lambda row: (
                row.occurrence,
                row.actor_label.casefold(),
                row.signal_semantic_key,
            )
        )
        return RaidReviewTankRecoveryResult(
            observations=tuple(observations),
            opportunities=tuple(opportunities),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _canonical_role(role: str) -> str:
        value = str(role or "").strip().casefold()
        if value in {"healer", "healing"}:
            return "Healer"
        if value in {"tank", "tanking"}:
            return "Tank"
        return "DPS"


__all__ = [
    "PerformanceRaidReviewTankRecoveryService",
    "RaidReviewTankRecoveryResult",
]
