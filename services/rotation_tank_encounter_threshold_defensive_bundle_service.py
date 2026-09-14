from __future__ import annotations

"""Compose projected health-threshold Tank defensive encounter obligations.

This service joins two existing authoritative lanes without creating a second health
clock. ``EncounterHealthThresholdProjection`` owns conversion from reviewed encounter
health thresholds plus explicit raid-damage trajectory evidence into seconds.
``RotationTankEncounterThresholdDefensiveTimingService`` binds those clock points to
reviewed defensive fact identity, while
``RotationTankEncounterDefensiveObligationService`` remains authoritative for Tank
applicability and explicit BLOCK/DODGE semantics.
"""

from dataclasses import dataclass

from services.encounter_evidence import ReconciledEncounterFact
from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjection,
)
from services.rotation_tank_defensive_obligation_service import (
    RotationTankDefensiveObligation,
)
from services.rotation_tank_encounter_defensive_obligation_service import (
    RotationTankEncounterDefensiveObligationService,
)
from services.rotation_tank_encounter_threshold_defensive_timing_service import (
    RotationTankEncounterThresholdDefensiveTimingPolicy,
    RotationTankEncounterThresholdDefensiveTimingService,
)


@dataclass(frozen=True)
class RotationTankEncounterThresholdDefensiveBundle:
    encounter_id: str
    obligations: tuple[RotationTankDefensiveObligation, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return bool(self.obligations) and not self.unresolved


class RotationTankEncounterThresholdDefensiveBundleService:
    """Resolve reviewed threshold-timed Tank defensive occurrences end to end."""

    def __init__(
        self,
        *,
        timing_service: RotationTankEncounterThresholdDefensiveTimingService | object | None = None,
        obligation_service: RotationTankEncounterDefensiveObligationService | object | None = None,
    ) -> None:
        self.timing_service = (
            timing_service or RotationTankEncounterThresholdDefensiveTimingService()
        )
        self.obligation_service = (
            obligation_service or RotationTankEncounterDefensiveObligationService()
        )

    def project(
        self,
        *,
        thresholds: EncounterHealthThresholdProjection,
        facts: tuple[ReconciledEncounterFact, ...],
        policies: tuple[RotationTankEncounterThresholdDefensiveTimingPolicy, ...],
    ) -> RotationTankEncounterThresholdDefensiveBundle:
        encounter_id = str(thresholds.encounter_id or "").strip()
        if not encounter_id:
            raise ValueError("threshold Tank defensive composition requires encounter_id")

        fact_by_identity: dict[tuple[str, str], ReconciledEncounterFact] = {}
        for fact in facts:
            if str(fact.encounter_id or "").strip().casefold() != encounter_id.casefold():
                continue
            key = (
                str(fact.fact_type or "").strip().casefold(),
                str(fact.fact_key or "").strip().casefold(),
            )
            if key in fact_by_identity:
                raise ValueError(
                    "duplicate reviewed threshold defensive fact identity for encounter: "
                    f"{key[0]} / {key[1]}"
                )
            fact_by_identity[key] = fact

        timing = self.timing_service.project(
            thresholds=thresholds,
            policies=tuple(policies),
        )
        unresolved: list[str] = list(timing.unresolved)
        obligations: list[RotationTankDefensiveObligation] = []

        for binding in timing.bindings:
            key = (binding.fact_type.casefold(), binding.fact_key.casefold())
            fact = fact_by_identity.get(key)
            if fact is None:
                unresolved.append(
                    f"{binding.occurrence_id}: reviewed defensive fact is missing for "
                    f"{binding.fact_type}/{binding.fact_key}"
                )
                continue

            projection = self.obligation_service.project(fact=fact, binding=binding)
            if projection.unresolved or projection.obligation is None:
                unresolved.extend(
                    f"{binding.occurrence_id}: {reason}"
                    for reason in (
                        projection.unresolved
                        or ("reviewed defensive fact did not produce an obligation",)
                    )
                )
                continue
            obligations.append(projection.obligation)

        obligations.sort(
            key=lambda item: (
                item.window_start_seconds,
                item.window_end_seconds,
                item.obligation_id,
            )
        )
        return RotationTankEncounterThresholdDefensiveBundle(
            encounter_id=encounter_id,
            obligations=tuple(obligations),
            unresolved=tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in unresolved
                    if str(item).strip()
                )
            ),
        )


__all__ = [
    "RotationTankEncounterThresholdDefensiveBundle",
    "RotationTankEncounterThresholdDefensiveBundleService",
]
