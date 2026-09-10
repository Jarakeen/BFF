from __future__ import annotations

"""Compose encounter threshold windows with reviewed healer criteria.

This module is intentionally orchestration only. Encounter health-threshold projection
owns when a reviewed health threshold occurs under the supplied raid-damage trajectory.
Threshold-demand policy owns the role preparation window around that point. Encounter
criteria evidence owns any numeric healer threshold and its review provenance.

No healing threshold, target multiplier, encounter timing, or survival claim is
invented here.
"""

from dataclasses import dataclass

from minmax.fight_damage_trajectory import RaidDamageSegment
from minmax.rotation_demand_window import RotationDemandWindow
from services.encounter_boss_guide import EncounterBossGuide
from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjection,
    EncounterHealthThresholdProjectionService,
)
from services.encounter_threshold_rotation_demand_service import (
    EncounterThresholdRotationDemandPolicy,
    EncounterThresholdRotationDemandProjection,
    EncounterThresholdRotationDemandService,
)
from services.rotation_healer_demand_criteria_service import RotationHealerDemandCriterion
from services.rotation_healer_encounter_criteria_provider import (
    RotationHealerEncounterCriteriaProjection,
    RotationHealerEncounterCriteriaProvider,
)


@dataclass(frozen=True)
class RotationHealerEncounterDemandBundle:
    encounter_id: str
    difficulty: str
    demands: tuple[RotationDemandWindow, ...]
    criteria: tuple[RotationHealerDemandCriterion, ...]
    threshold_projection: EncounterHealthThresholdProjection
    demand_projection: EncounterThresholdRotationDemandProjection
    criteria_projection: RotationHealerEncounterCriteriaProjection
    unresolved: tuple[str, ...] = ()


class RotationHealerEncounterDemandBundleService:
    """Build one encounter-aware healer input package from existing canonical layers.

    Criteria are scoped to the demand-policy names supplied by the caller. A reviewed
    criterion whose selected demand cannot be projected remains in the bundle so the
    downstream hard gate can fail closed rather than silently dropping an encounter
    obligation. Criteria for unrelated encounter windows are ignored by this bundle.
    """

    def __init__(
        self,
        *,
        criteria_provider: RotationHealerEncounterCriteriaProvider,
        threshold_projection_service: EncounterHealthThresholdProjectionService | None = None,
        demand_projection_service: EncounterThresholdRotationDemandService | None = None,
    ) -> None:
        self.criteria_provider = criteria_provider
        self.threshold_projection_service = (
            threshold_projection_service or EncounterHealthThresholdProjectionService()
        )
        self.demand_projection_service = (
            demand_projection_service or EncounterThresholdRotationDemandService()
        )

    def project(
        self,
        *,
        guide: EncounterBossGuide,
        difficulty: str,
        damage_segments: tuple[RaidDamageSegment, ...],
        demand_policies: tuple[EncounterThresholdRotationDemandPolicy, ...],
        reviewed_fact_ids: tuple[str, ...] = (),
    ) -> RotationHealerEncounterDemandBundle:
        policies = tuple(demand_policies)
        if not policies:
            raise ValueError("healer encounter demand bundle requires at least one demand policy")
        if any(policy.kind.value != "healing" for policy in policies):
            raise ValueError("healer encounter demand bundle accepts only healing demand policies")

        threshold_projection = self.threshold_projection_service.project(
            guide=guide,
            difficulty=difficulty,
            damage_segments=tuple(damage_segments),
        )
        if threshold_projection.encounter_id != guide.encounter_id:
            raise ValueError("healer encounter threshold projection encounter mismatch")

        demand_projection = self.demand_projection_service.project(
            thresholds=threshold_projection,
            policies=policies,
        )
        if demand_projection.encounter_id != guide.encounter_id:
            raise ValueError("healer encounter demand projection encounter mismatch")

        criteria_projection = self.criteria_provider.criteria_for_encounter(
            encounter_id=guide.encounter_id,
            reviewed_fact_ids=tuple(reviewed_fact_ids),
        )
        if criteria_projection.encounter_id != guide.encounter_id:
            raise ValueError("healer encounter criteria projection encounter mismatch")

        policy_names = {
            (policy.name or "").strip().casefold()
            for policy in policies
            if (policy.name or "").strip()
        }
        criteria = tuple(
            criterion
            for criterion in criteria_projection.criteria
            if criterion.demand_name.casefold() in policy_names
        )

        unresolved = tuple(
            dict.fromkeys(
                tuple(threshold_projection.unresolved)
                + tuple(demand_projection.unresolved)
                + tuple(criteria_projection.unresolved)
            )
        )

        return RotationHealerEncounterDemandBundle(
            encounter_id=guide.encounter_id,
            difficulty=threshold_projection.difficulty,
            demands=tuple(demand_projection.demands),
            criteria=criteria,
            threshold_projection=threshold_projection,
            demand_projection=demand_projection,
            criteria_projection=criteria_projection,
            unresolved=unresolved,
        )


__all__ = [
    "RotationHealerEncounterDemandBundle",
    "RotationHealerEncounterDemandBundleService",
]
