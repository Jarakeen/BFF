from __future__ import annotations

from dataclasses import dataclass

from .combat_damage_modifiers import damage_done_from_combat_state
from .combat_state import CombatState
from .damage_done import DamageDoneModifiers
from .dd_damage import (
    DDDamageEvent,
    DDDamageResult,
    calculate_dd_damage,
)
from .dd_mitigation import DDMitigationResult
from .dd_stat_evaluation import DDStatEvaluation
from .skill_damage import SkillDamageResult


@dataclass(frozen=True)
class SkillCombatDamageResult:
    """Final, explainable combat damage for one skill rank."""

    skill_rank_id: int
    damage_type: str | None
    raw_skill_damage: float
    damage: DDDamageResult


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
    damage_done: DamageDoneModifiers | None = None,
) -> SkillCombatDamageResult:
    """Connect database-backed skill damage to the authoritative DD pipeline.

    ``SkillDamageService.evaluate`` already scales active coefficients by the
    caller-supplied max-stat/power, so ``total_raw_damage`` is passed as an
    already-scaled event value. Damage Done is then resolved by event identity,
    followed by expected critical damage and target mitigation.

    If ``damage_done`` is supplied explicitly it is authoritative. Otherwise
    verified named Damage Done buffs are resolved from ``combat_state``. This
    keeps a selected potion or merely available buff from becoming active by
    implication.
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

    resolved_damage_done = (
        damage_done
        if damage_done is not None
        else damage_done_from_combat_state(combat_state)
    )

    damage = calculate_dd_damage(
        event,
        stats,
        mitigation=mitigation,
        damage_done=resolved_damage_done,
    )

    return SkillCombatDamageResult(
        skill_rank_id=skill_damage.skill_rank_id,
        damage_type=damage_type,
        raw_skill_damage=skill_damage.total_raw_damage,
        damage=damage,
    )
