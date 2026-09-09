from __future__ import annotations

"""Measure distinct reviewed Lokkestiiz landing-recovery obligations.

The generic landing-recovery service answers when a role resumes useful work.  This
adapter keeps separate obligations separate so Horn timing, boss-debuff reapplication,
Major Brittle reapplication, and DD boss reacquisition can be compared independently.

Numeric ESO ability IDs are deliberately absent.  Reviewed raw IDs may identify the
encounter boundary upstream, but semantic player actions here use translated names or
an explicit boss-target rule.
"""

from dataclasses import dataclass
from typing import Iterable

from services.performance_raid_review_landing_recovery_service import (
    PerformanceRaidReviewLandingRecoveryService,
    RaidReviewLandingRecoveryObservation,
    RaidReviewRecoveryActor,
    RaidReviewRecoverySignal,
)
from services.rotation_lokkestiiz_landing_clock_service import EncounterObservedClockBoundary


@dataclass(frozen=True, slots=True)
class LokkestiizRecoveryObligationResult:
    observations: tuple[RaidReviewLandingRecoveryObservation, ...]
    unresolved: tuple[str, ...] = ()


class PerformanceRaidReviewLokkestiizRecoveryObligationService:
    """Resolve each reviewed Lokke landing obligation independently."""

    def __init__(
        self,
        *,
        recovery_service: PerformanceRaidReviewLandingRecoveryService | None = None,
    ) -> None:
        self.recovery_service = recovery_service or PerformanceRaidReviewLandingRecoveryService()

    @staticmethod
    def reviewed_signals() -> tuple[RaidReviewRecoverySignal, ...]:
        return (
            RaidReviewRecoverySignal(
                semantic_key="aggressive_horn_after_landing",
                label="Aggressive Horn",
                role="Healer",
                event_types=("cast",),
                ability_names=("Aggressive Horn",),
            ),
            RaidReviewRecoverySignal(
                semantic_key="elemental_susceptibility_after_landing",
                label="Elemental Susceptibility",
                role="Healer",
                event_types=("cast", "applydebuff", "refreshdebuff"),
                ability_names=("Elemental Susceptibility",),
            ),
            RaidReviewRecoverySignal(
                semantic_key="major_brittle_after_landing",
                label="Major Brittle",
                role="Healer",
                event_types=("applydebuff", "refreshdebuff", "applybuff", "refreshbuff"),
                ability_names=("Major Brittle",),
            ),
            RaidReviewRecoverySignal(
                semantic_key="boss_damage_reacquisition_after_landing",
                label="Boss Damage Reacquisition",
                role="DPS",
                event_types=("damage", "calculateddamage"),
                require_boss_target=True,
            ),
        )

    def measure(
        self,
        *,
        report_code: str,
        fight_id: int,
        fight_start_time_ms: float,
        events: Iterable[dict],
        landing_boundaries: Iterable[EncounterObservedClockBoundary],
        actors: Iterable[RaidReviewRecoveryActor],
        boss_actor_id: int | None,
        max_delay_seconds: float = 15.0,
    ) -> LokkestiizRecoveryObligationResult:
        rows = tuple(event for event in events if isinstance(event, dict))
        boundaries = tuple(landing_boundaries)
        actor_rows = tuple(actors)
        observations: list[RaidReviewLandingRecoveryObservation] = []
        unresolved: list[str] = []

        for signal in self.reviewed_signals():
            matching_actors = tuple(
                actor for actor in actor_rows
                if self._canonical_role(actor.role) == self._canonical_role(signal.role)
            )
            if not matching_actors:
                continue

            result = self.recovery_service.measure(
                report_code=report_code,
                fight_id=fight_id,
                fight_start_time_ms=fight_start_time_ms,
                events=rows,
                landing_boundaries=boundaries,
                actors=matching_actors,
                signals=(signal,),
                boss_actor_id=boss_actor_id,
                max_delay_seconds=max_delay_seconds,
            )
            observations.extend(result.observations)
            unresolved.extend(result.unresolved)

        observations.sort(
            key=lambda item: (
                item.occurrence,
                item.role,
                item.actor_label.casefold(),
                item.signal_semantic_key,
            )
        )
        return LokkestiizRecoveryObligationResult(
            observations=tuple(observations),
            unresolved=tuple(unresolved),
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
    "LokkestiizRecoveryObligationResult",
    "PerformanceRaidReviewLokkestiizRecoveryObligationService",
]
