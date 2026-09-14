from __future__ import annotations

"""Bind projected encounter health thresholds to tank defensive mechanics.

The existing encounter threshold projection owns conversion from reviewed health
thresholds plus an explicit raid-damage trajectory into clock points. The existing
threshold rotation-demand service owns the resulting role window. This adapter only
associates one such resolved window with a separately reviewed tank defensive fact.
"""

from dataclasses import dataclass
import math

from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjection,
)
from services.encounter_threshold_rotation_demand_service import (
    EncounterThresholdRotationDemandPolicy,
    EncounterThresholdRotationDemandService,
)
from services.rotation_tank_encounter_defensive_obligation_service import (
    RotationTankEncounterDefensiveWindowBinding,
)
from services.rotation_tank_encounter_defensive_timing_service import (
    RotationTankEncounterDefensiveTimingProjection,
)


@dataclass(frozen=True)
class RotationTankEncounterThresholdDefensiveTimingPolicy:
    """Explicit link between one projected health threshold and one defensive fact."""

    occurrence_id: str
    threshold_fact_key: str
    threshold_fraction: float
    defensive_fact_type: str
    defensive_fact_key: str
    lead_seconds: float = 0.0
    window_seconds: float = 1.0
    minimum_responses: int = 1
    bar: str | None = None

    def __post_init__(self) -> None:
        occurrence_id = str(self.occurrence_id or "").strip()
        threshold_fact_key = str(self.threshold_fact_key or "").strip()
        defensive_fact_type = str(self.defensive_fact_type or "").strip().casefold()
        defensive_fact_key = str(self.defensive_fact_key or "").strip().casefold()
        if not occurrence_id:
            raise ValueError("tank threshold defensive timing occurrence_id is required")
        if not threshold_fact_key:
            raise ValueError("tank threshold defensive timing threshold_fact_key is required")
        if not defensive_fact_type:
            raise ValueError("tank threshold defensive timing defensive_fact_type is required")
        if not defensive_fact_key:
            raise ValueError("tank threshold defensive timing defensive_fact_key is required")
        object.__setattr__(self, "occurrence_id", occurrence_id)
        object.__setattr__(self, "threshold_fact_key", threshold_fact_key)
        object.__setattr__(self, "defensive_fact_type", defensive_fact_type)
        object.__setattr__(self, "defensive_fact_key", defensive_fact_key)

        threshold = float(self.threshold_fraction)
        if not math.isfinite(threshold) or not 0 < threshold < 1:
            raise ValueError(
                "tank threshold defensive timing threshold_fraction must be finite and between 0 and 1"
            )
        object.__setattr__(self, "threshold_fraction", threshold)

        lead = float(self.lead_seconds)
        width = float(self.window_seconds)
        if not math.isfinite(lead) or lead < 0:
            raise ValueError(
                "tank threshold defensive timing lead_seconds must be finite and non-negative"
            )
        if not math.isfinite(width) or width <= 0:
            raise ValueError(
                "tank threshold defensive timing window_seconds must be finite and positive"
            )
        object.__setattr__(self, "lead_seconds", lead)
        object.__setattr__(self, "window_seconds", width)

        minimum = int(self.minimum_responses)
        if minimum < 1:
            raise ValueError(
                "tank threshold defensive timing minimum_responses must be positive"
            )
        object.__setattr__(self, "minimum_responses", minimum)

        if self.bar is not None:
            bar = str(self.bar or "").strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError(
                    "tank threshold defensive timing bar must be front or back"
                )
            object.__setattr__(self, "bar", bar)


class RotationTankEncounterThresholdDefensiveTimingService:
    """Reuse projected health-threshold windows for tank defensive bindings."""

    def __init__(
        self,
        demand_service: EncounterThresholdRotationDemandService | None = None,
    ) -> None:
        self.demand_service = demand_service or EncounterThresholdRotationDemandService()

    def project(
        self,
        *,
        thresholds: EncounterHealthThresholdProjection,
        policies: tuple[RotationTankEncounterThresholdDefensiveTimingPolicy, ...],
    ) -> RotationTankEncounterDefensiveTimingProjection:
        seen_occurrences: set[str] = set()
        bindings: list[RotationTankEncounterDefensiveWindowBinding] = []
        unresolved: list[str] = []

        for policy in policies:
            if policy.occurrence_id in seen_occurrences:
                raise ValueError(
                    "duplicate tank threshold defensive timing occurrence_id: "
                    f"{policy.occurrence_id}"
                )
            seen_occurrences.add(policy.occurrence_id)

            timing = self.demand_service.project(
                thresholds=thresholds,
                policies=(
                    EncounterThresholdRotationDemandPolicy(
                        fact_key=policy.threshold_fact_key,
                        threshold_fraction=policy.threshold_fraction,
                        kind=RotationDemandKind.MITIGATION,
                        pattern=RotationDemandPattern.BURST,
                        lead_seconds=policy.lead_seconds,
                        window_seconds=policy.window_seconds,
                        target_count=1,
                        name=policy.occurrence_id,
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
                    f"{policy.occurrence_id}: projected health-threshold timing did not resolve exactly one window"
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
            encounter_id=thresholds.encounter_id,
            bindings=tuple(bindings),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "RotationTankEncounterThresholdDefensiveTimingPolicy",
    "RotationTankEncounterThresholdDefensiveTimingService",
]
