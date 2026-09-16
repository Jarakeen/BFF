from __future__ import annotations

"""Compose candidate-heal scope into explicit H1 gear condition markers."""

from dataclasses import dataclass
from pathlib import Path

from minmax.gear_stat_inputs import GearStatInputResolver
from models.build_model import PlayerBuild
from services.extreme_actual_heal_candidate_scope_service import (
    ExtremeActualHealCandidateScopeService,
)
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    INNATE_AXIOM_CLASS_SCOPE_CONDITION,
    LIGHT_SPEAKER_RESTORATION_SCOPE_CONDITION,
)


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
    ) -> None:
        self.scope_service = scope_service or ExtremeActualHealCandidateScopeService(database_path)

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
                for name in ("Light Speaker", "Innate Axiom")
            )
            unresolved = (
                f"selected heal scope identity is unavailable for {entity_id}",
            ) if relevant else ()
            return ExtremeActualHealCandidateGearCondition(unresolved=unresolved)

        active: list[str] = []
        evidence: list[str] = []
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

        return ExtremeActualHealCandidateGearCondition(
            active_conditions=tuple(active),
            evidence=tuple(evidence),
            unresolved=(),
        )


__all__ = [
    "ExtremeActualHealCandidateGearCondition",
    "ExtremeActualHealCandidateGearConditionService",
]
