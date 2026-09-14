from __future__ import annotations

"""Bind canonical encounter clock evidence to reviewed tank defensive mechanics.

The existing EncounterRotationDemandService remains the sole owner of converting
reviewed canonical timeline facts into clock windows. This adapter only associates
one such window with a separately reviewed defensive mechanic fact. It therefore
keeps two independent questions separate:

* when does this mechanic occurrence happen?
* what defensive response does the mechanic support for a tank?

Neither answer is inferred from prose, fact names, health thresholds, or the other
answer.
"""

from dataclasses import dataclass
import math

from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from services.encounter_boss_guide import EncounterBossGuide
from services.encounter_rotation_demand_service import (
    EncounterRotationDemandPolicy,
    EncounterRotationDemandService,
)
from services.rotation_tank_encounter_defensive_obligation_service import (
    RotationTankEncounterDefensiveWindowBinding,
)


@dataclass(frozen=True)
class RotationTankEncounterDefensiveTimingPolicy:
    """Explicit link between one canonical clock fact and one defensive fact."""

    occurrence_id: str
    timeline_fact_key: str
    defensive_fact_type: str
    defensive_fact_key: str
    lead_seconds: float = 0.0
    point_window_seconds: float | None = None
    minimum_responses: int = 1
    bar: str | None = None

    def __post_init__(self) -> None:
        occurrence_id = str(self.occurrence_id or "").strip()
        timeline_fact_key = str(self.timeline_fact_key or "").strip()
        defensive_fact_type = str(self.defensive_fact_type or "").strip().casefold()
        defensive_fact_key = str(self.defensive_fact_key or "").strip().casefold()
        if not occurrence_id:
            raise ValueError("tank defensive timing policy occurrence_id is required")
        if not timeline_fact_key:
            raise ValueError("tank defensive timing policy timeline_fact_key is required")
        if not defensive_fact_type:
            raise ValueError("tank defensive timing policy defensive_fact_type is required")
        if not defensive_fact_key:
            raise ValueError("tank defensive timing policy defensive_fact_key is required")
        object.__setattr__(self, "occurrence_id", occurrence_id)
        object.__setattr__(self, "timeline_fact_key", timeline_fact_key)
        object.__setattr__(self, "defensive_fact_type", defensive_fact_type)
        object.__setattr__(self, "defensive_fact_key", defensive_fact_key)

        lead = float(self.lead_seconds)
        if not math.isfinite(lead) or lead < 0:
            raise ValueError("tank defensive timing lead_seconds must be finite and non-negative")
        object.__setattr__(self, "lead_seconds", lead)

        if self.point_window_seconds is not None:
            width = float(self.point_window_seconds)
            if not math.isfinite(width) or width <= 0:
                raise ValueError(
                    "tank defensive timing point_window_seconds must be finite and positive"
                )
            object.__setattr__(self, "point_window_seconds", width)

        minimum = int(self.minimum_responses)
        if minimum < 1:
            raise ValueError("tank defensive timing minimum_responses must be positive")
        object.__setattr__(self, "minimum_responses", minimum)

        if self.bar is not None:
            bar = str(self.bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("tank defensive timing bar must be front or back")
            object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class RotationTankEncounterDefensiveTimingProjection:
    encounter_id: str
    bindings: tuple[RotationTankEncounterDefensiveWindowBinding, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return bool(self.bindings) and not self.unresolved


class RotationTankEncounterDefensiveTimingService:
    """Reuse canonical encounter timing to create tank defensive window bindings."""

    def __init__(
        self,
        demand_service: EncounterRotationDemandService | None = None,
    ) -> None:
        self.demand_service = demand_service or EncounterRotationDemandService()

    def project(
        self,
        *,
        guide: EncounterBossGuide,
        policies: tuple[RotationTankEncounterDefensiveTimingPolicy, ...],
    ) -> RotationTankEncounterDefensiveTimingProjection:
        seen_occurrences: set[str] = set()
        bindings: list[RotationTankEncounterDefensiveWindowBinding] = []
        unresolved: list[str] = []

        for policy in policies:
            if policy.occurrence_id in seen_occurrences:
                raise ValueError(
                    f"duplicate tank defensive timing occurrence_id: {policy.occurrence_id}"
                )
            seen_occurrences.add(policy.occurrence_id)

            timing = self.demand_service.project(
                guide=guide,
                policies=(
                    EncounterRotationDemandPolicy(
                        fact_key=policy.timeline_fact_key,
                        kind=RotationDemandKind.MITIGATION,
                        pattern=RotationDemandPattern.BURST,
                        lead_seconds=policy.lead_seconds,
                        point_window_seconds=policy.point_window_seconds,
                        target_count=1,
                    ),
                ),
            )
            if timing.unresolved:
                unresolved.extend(
                    f"{policy.occurrence_id}: {reason}" for reason in timing.unresolved
                )
                continue
            if len(timing.demands) != 1:
                unresolved.append(
                    f"{policy.occurrence_id}: canonical encounter timing did not resolve exactly one window"
                )
                continue

            demand = timing.demands[0]
            bindings.append(
                RotationTankEncounterDefensiveWindowBinding(
                    occurrence_id=policy.occurrence_id,
                    fact_type=policy.defensive_fact_type,
                    fact_key=policy.defensive_fact_key,
                    window_start_seconds=demand.start_seconds,
                    window_end_seconds=demand.end_seconds,
                    minimum_responses=policy.minimum_responses,
                    bar=policy.bar,
                )
            )

        bindings.sort(
            key=lambda item: (
                item.window_start_seconds,
                item.window_end_seconds,
                item.occurrence_id,
            )
        )
        return RotationTankEncounterDefensiveTimingProjection(
            encounter_id=guide.encounter_id,
            bindings=tuple(bindings),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "RotationTankEncounterDefensiveTimingPolicy",
    "RotationTankEncounterDefensiveTimingProjection",
    "RotationTankEncounterDefensiveTimingService",
]
