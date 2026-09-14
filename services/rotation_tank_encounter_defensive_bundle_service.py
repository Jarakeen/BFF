from __future__ import annotations

"""Compose reviewed clock-timed Tank defensive encounter obligations.

This service joins two already-authoritative lanes without creating new ESO truth:
reviewed canonical encounter timing and separately reviewed structured defensive
mechanic facts. Timing remains owned by RotationTankEncounterDefensiveTimingService;
block/dodge semantics and tank applicability remain owned by
RotationTankEncounterDefensiveObligationService.
"""

from dataclasses import dataclass

from services.encounter_boss_guide import EncounterBossGuide
from services.encounter_evidence import ReconciledEncounterFact
from services.rotation_tank_defensive_obligation_service import (
    RotationTankDefensiveObligation,
)
from services.rotation_tank_encounter_defensive_obligation_service import (
    RotationTankEncounterDefensiveObligationService,
)
from services.rotation_tank_encounter_defensive_timing_service import (
    RotationTankEncounterDefensiveTimingPolicy,
    RotationTankEncounterDefensiveTimingService,
)


@dataclass(frozen=True)
class RotationTankEncounterDefensiveBundle:
    encounter_id: str
    obligations: tuple[RotationTankDefensiveObligation, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return bool(self.obligations) and not self.unresolved


class RotationTankEncounterDefensiveBundleService:
    """Resolve reviewed explicit-clock Tank defensive occurrences end to end."""

    def __init__(
        self,
        *,
        timing_service: RotationTankEncounterDefensiveTimingService | object | None = None,
        obligation_service: RotationTankEncounterDefensiveObligationService | object | None = None,
    ) -> None:
        self.timing_service = timing_service or RotationTankEncounterDefensiveTimingService()
        self.obligation_service = obligation_service or RotationTankEncounterDefensiveObligationService()

    def project(
        self,
        *,
        guide: EncounterBossGuide,
        facts: tuple[ReconciledEncounterFact, ...],
        policies: tuple[RotationTankEncounterDefensiveTimingPolicy, ...],
    ) -> RotationTankEncounterDefensiveBundle:
        fact_by_identity: dict[tuple[str, str], ReconciledEncounterFact] = {}
        for fact in facts:
            if str(fact.encounter_id or "").strip().casefold() != guide.encounter_id.casefold():
                continue
            key = (
                str(fact.fact_type or "").strip().casefold(),
                str(fact.fact_key or "").strip().casefold(),
            )
            if key in fact_by_identity:
                raise ValueError(
                    "duplicate reviewed defensive fact identity for encounter: "
                    f"{key[0]} / {key[1]}"
                )
            fact_by_identity[key] = fact

        timing = self.timing_service.project(guide=guide, policies=tuple(policies))
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
        return RotationTankEncounterDefensiveBundle(
            encounter_id=guide.encounter_id,
            obligations=tuple(obligations),
            unresolved=tuple(dict.fromkeys(str(item).strip() for item in unresolved if str(item).strip())),
        )


__all__ = [
    "RotationTankEncounterDefensiveBundle",
    "RotationTankEncounterDefensiveBundleService",
]
