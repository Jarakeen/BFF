from __future__ import annotations

from dataclasses import dataclass

from .combat_damage_modifiers import (
    damage_done_from_combat_state,
    damage_taken_from_target_state,
)
from .combat_state import CombatState
from .damage_done import DamageDoneModifiers
from .damage_taken import DamageTakenModifiers
from .dd_damage import (
    DDDamageEvent,
    DDDamageResult,
    calculate_dd_damage,
)
from .dd_mitigation import DDMitigationResult
from .dd_stat_evaluation import DDStatEvaluation
from .skill_component_classification import SkillComponentClassification
from .skill_damage import SkillDamageResult


@dataclass(frozen=True)
class SkillCombatDamageResult:
    """Final, explainable combat damage for one skill rank."""

    skill_rank_id: int
    damage_type: str | None
    raw_skill_damage: float
    damage: DDDamageResult


@dataclass(frozen=True)
class SkillCombatComponentResult:
    """Combat result for one verified coefficient-bearing damage component."""

    coefficient_number: int
    raw_component_value: float
    classification: SkillComponentClassification
    damage: DDDamageResult


@dataclass(frozen=True)
class ClassifiedSkillCombatDamageResult:
    """Per-component combat evaluation without whole-skill identity guessing."""

    skill_rank_id: int
    components: tuple[SkillCombatComponentResult, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def raw_damage(self) -> float:
        return sum(component.raw_component_value for component in self.components)

    @property
    def final_damage(self) -> float:
        return sum(component.damage.final_damage for component in self.components)


def _resolved_modifier_inputs(
    *,
    combat_state: CombatState | None,
    target_combat_state: CombatState | None,
    damage_done: DamageDoneModifiers | None,
    damage_taken: DamageTakenModifiers | None,
) -> tuple[DamageDoneModifiers, DamageTakenModifiers]:
    return (
        damage_done
        if damage_done is not None
        else damage_done_from_combat_state(combat_state),
        damage_taken
        if damage_taken is not None
        else damage_taken_from_target_state(target_combat_state),
    )


def calculate_skill_combat_damage(
    skill_damage: SkillDamageResult,
    stats: DDStatEvaluation,
    *,
    damage_type: str | None = None,
    can_crit: bool = True,
    is_dot: bool = False,
    is_aoe: bool = False,
    mitigation: DDMitigationResult | None = None,
    combat_state: CombatState | None = None,
    target_combat_state: CombatState | None = None,
    damage_done: DamageDoneModifiers | None = None,
    damage_taken: DamageTakenModifiers | None = None,
) -> SkillCombatDamageResult:
    """Connect aggregate skill damage to the authoritative DD pipeline.

    This compatibility path remains available for callers that explicitly know
    a whole skill's event identity. New database-backed work should prefer
    ``calculate_classified_skill_combat_damage`` so mechanically different
    coefficient components are routed independently.
    """

    if skill_damage.total_raw_damage < 0:
        raise ValueError("Skill raw damage cannot be negative.")

    event = DDDamageEvent(
        base_value=skill_damage.total_raw_damage,
        scaling_coefficient=0.0,
        damage_type=damage_type,
        can_crit=can_crit,
        is_dot=is_dot,
        is_aoe=is_aoe,
    )

    resolved_damage_done, resolved_damage_taken = _resolved_modifier_inputs(
        combat_state=combat_state,
        target_combat_state=target_combat_state,
        damage_done=damage_done,
        damage_taken=damage_taken,
    )

    damage = calculate_dd_damage(
        event,
        stats,
        mitigation=mitigation,
        damage_done=resolved_damage_done,
        damage_taken=resolved_damage_taken,
    )

    return SkillCombatDamageResult(
        skill_rank_id=skill_damage.skill_rank_id,
        damage_type=damage_type,
        raw_skill_damage=skill_damage.total_raw_damage,
        damage=damage,
    )


def calculate_classified_skill_combat_damage(
    skill_damage: SkillDamageResult,
    stats: DDStatEvaluation,
    classifications: tuple[SkillComponentClassification, ...],
    *,
    mitigation: DDMitigationResult | None = None,
    combat_state: CombatState | None = None,
    target_combat_state: CombatState | None = None,
    damage_done: DamageDoneModifiers | None = None,
    damage_taken: DamageTakenModifiers | None = None,
) -> ClassifiedSkillCombatDamageResult:
    """Evaluate only coefficient components with complete verified damage identity.

    Missing or incomplete component metadata is returned as unresolved evidence;
    it is never filled from skill names, duration, target strings, or neighboring
    components. Non-damage components are intentionally excluded from this
    damage-only result so later heal/shield evaluators can own their semantics.
    """

    by_number = {item.coefficient_number: item for item in classifications}
    resolved_damage_done, resolved_damage_taken = _resolved_modifier_inputs(
        combat_state=combat_state,
        target_combat_state=target_combat_state,
        damage_done=damage_done,
        damage_taken=damage_taken,
    )

    results: list[SkillCombatComponentResult] = []
    unresolved: list[str] = []

    for component in skill_damage.components:
        number = int(component.coefficient_number)
        classification = by_number.get(number)
        if classification is None:
            unresolved.append(
                f"Skill rank {skill_damage.skill_rank_id} coefficient {number}: component classification unavailable"
            )
            continue
        if not classification.is_damage:
            continue
        if not classification.is_complete_damage_identity:
            unresolved.append(
                f"Skill rank {skill_damage.skill_rank_id} coefficient {number}: damage classification incomplete"
            )
            continue

        raw_value = float(component.scaled_value)
        if raw_value < 0:
            raise ValueError(
                f"Skill rank {skill_damage.skill_rank_id} coefficient {number}: raw damage cannot be negative"
            )

        event = DDDamageEvent(
            base_value=raw_value,
            scaling_coefficient=0.0,
            damage_type=classification.damage_type,
            can_crit=bool(classification.can_crit),
            is_dot=bool(classification.is_dot),
            is_aoe=bool(classification.is_aoe),
        )
        damage = calculate_dd_damage(
            event,
            stats,
            mitigation=mitigation,
            damage_done=resolved_damage_done,
            damage_taken=resolved_damage_taken,
        )
        results.append(
            SkillCombatComponentResult(
                coefficient_number=number,
                raw_component_value=raw_value,
                classification=classification,
                damage=damage,
            )
        )

    return ClassifiedSkillCombatDamageResult(
        skill_rank_id=skill_damage.skill_rank_id,
        components=tuple(results),
        unresolved=tuple(unresolved),
    )
