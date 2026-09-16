from __future__ import annotations

"""Compose candidate-heal scope into explicit H1 gear condition markers."""

from dataclasses import dataclass
from pathlib import Path

from minmax.gear_set_healing_condition_resolver import BLIND_PATH_DISTANT_HEAL_CONDITION
from minmax.gear_stat_inputs import GearStatInputResolver
from models.build_model import PlayerBuild
from services.extreme_actual_heal_candidate_distance_service import (
    ExtremeActualHealCandidateDistanceService,
)
from services.extreme_actual_heal_candidate_scope_service import (
    ExtremeActualHealCandidateScopeService,
)
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    INNATE_AXIOM_CLASS_SCOPE_CONDITION,
    LIGHT_SPEAKER_RESTORATION_SCOPE_CONDITION,
)


DAGON_AREA_SCOPE_CONDITION = "ability_scope:area_of_effect"
BLIND_PATH_DISTANCE_THRESHOLD_METERS = 15.0


@dataclass(frozen=True)
class ExtremeActualHealCandidateGearCondition:
    active_conditions: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def condition_context(self) -> frozenset[str]:
        return frozenset(self.active_conditions)


class ExtremeActualHealCandidateGearConditionService:
    """Activate reviewed scoped-set effects only for the selected heal identity."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        scope_service: ExtremeActualHealCandidateScopeService | None = None,
        distance_service: ExtremeActualHealCandidateDistanceService | None = None,
    ) -> None:
        self.scope_service = scope_service or ExtremeActualHealCandidateScopeService(database_path)
        self.distance_service = distance_service or ExtremeActualHealCandidateDistanceService(database_path)

    def resolve(
        self,
        build: PlayerBuild,
        entity_id: str,
        *,
        active_bar: str = "front",
    ) -> ExtremeActualHealCandidateGearCondition:
        counts = GearStatInputResolver.equipped_set_counts(build, active_bar=active_bar)
        scope = self.scope_service.resolve_entity(entity_id)
        if scope is None:
            relevant = any(
                int(counts.get(name, 0)) >= 5
                for name in ("Light Speaker", "Innate Axiom", "Dagon's Dominion")
            )
            unresolved = (
                f"selected heal scope identity is unavailable for {entity_id}",
            ) if relevant else ()
            active: list[str] = []
            evidence: list[str] = []
            if int(counts.get("Blind Path Induction", 0)) >= 5:
                distance = self.distance_service.resolve(
                    entity_id,
                    threshold_meters=BLIND_PATH_DISTANCE_THRESHOLD_METERS,
                )
                if distance.can_affect_target_beyond_threshold is True:
                    active.append(BLIND_PATH_DISTANT_HEAL_CONDITION)
                    evidence.extend(distance.evidence)
                elif distance.can_affect_target_beyond_threshold is None:
                    unresolved = tuple(dict.fromkeys((*unresolved, *distance.unresolved)))
            return ExtremeActualHealCandidateGearCondition(
                active_conditions=tuple(active),
                evidence=tuple(evidence),
                unresolved=unresolved,
            )

        active: list[str] = []
        evidence: list[str] = []
        unresolved: list[str] = []
        if int(counts.get("Light Speaker", 0)) >= 5 and scope.is_restoration_staff_ability:
            active.append(LIGHT_SPEAKER_RESTORATION_SCOPE_CONDITION)
            evidence.append(
                f"{LIGHT_SPEAKER_RESTORATION_SCOPE_CONDITION}: selected heal {entity_id} "
                "is canonically a Restoration Staff ability"
            )

        if int(counts.get("Innate Axiom", 0)) >= 5 and scope.is_class_ability:
            active.append(INNATE_AXIOM_CLASS_SCOPE_CONDITION)
            evidence.append(
                f"{INNATE_AXIOM_CLASS_SCOPE_CONDITION}: selected heal {entity_id} "
                "is canonically a class ability"
            )

        if int(counts.get("Dagon's Dominion", 0)) >= 5:
            if scope.is_area_of_effect is True:
                active.append(DAGON_AREA_SCOPE_CONDITION)
                evidence.append(
                    f"{DAGON_AREA_SCOPE_CONDITION}: selected heal {entity_id} "
                    "has canonical reviewed AoE HEAL-component classification"
                )
            elif scope.is_area_of_effect is None:
                unresolved.extend(scope.unresolved or (
                    f"selected heal AoE identity is unavailable for {entity_id}",
                ))

        if int(counts.get("Blind Path Induction", 0)) >= 5:
            distance = self.distance_service.resolve(
                entity_id,
                threshold_meters=BLIND_PATH_DISTANCE_THRESHOLD_METERS,
            )
            if distance.can_affect_target_beyond_threshold is True:
                active.append(BLIND_PATH_DISTANT_HEAL_CONDITION)
                evidence.extend(distance.evidence)
            elif distance.can_affect_target_beyond_threshold is None:
                unresolved.extend(distance.unresolved or (
                    f"selected heal distance identity is unavailable for {entity_id}",
                ))

        return ExtremeActualHealCandidateGearCondition(
            active_conditions=tuple(active),
            evidence=tuple(evidence),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "BLIND_PATH_DISTANCE_THRESHOLD_METERS",
    "DAGON_AREA_SCOPE_CONDITION",
    "ExtremeActualHealCandidateGearCondition",
    "ExtremeActualHealCandidateGearConditionService",
]
