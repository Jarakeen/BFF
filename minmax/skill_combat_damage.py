from __future__ import annotations

from dataclasses import dataclass

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
    """
    Final, explainable combat damage for one skill rank.

    Carries the database-backed raw skill damage alongside the
    fully resolved ``DDDamageResult`` so callers (and, eventually,
    the Optimization UI) can explain a recommendation in terms of
    each stage of the pipeline: raw skill damage -> expected damage
    (crit) -> mitigated damage (penetration/resistance).
    """

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
    mitigation: DDMitigationResult | None = None,
) -> SkillCombatDamageResult:
    """
    Connect database-backed skill damage to the DD combat-math layer.

    This is the missing link in the pipeline described by Phase 5:

        skill/morph
        -> database coefficient          (minmax.skill_coefficient)
        -> character scaling stats
        -> raw component value           (minmax.skill_damage)
        -> applicable modifiers (crit)   (minmax.dd_damage)
        -> target mitigation             (minmax.dd_mitigation)
        -> final result

    ``SkillDamageService.evaluate`` already scales every active
    coefficient by the caller-supplied max-stat/power (see
    ``evaluate_skill_coefficient``), so ``skill_damage.total_raw_damage``
    is a fully-scaled value, not a base tooltip value awaiting a
    scaling coefficient. It is therefore passed to ``DDDamageEvent``
    as ``base_value`` with ``scaling_coefficient=0.0`` -- reusing
    ``calculate_dd_damage``'s own offensive-power scaling here would
    double-apply weapon/spell damage on top of what the database
    coefficient already scaled.

    ``damage_type`` still selects which offensive/penetration stat
    pairing (weapon vs. spell) applies for crit-stat bookkeeping and
    which penetration figure feeds ``mitigation``, via
    ``minmax.dd_damage_profile``. Passing ``damage_type=None`` mirrors
    ``dd_damage``'s own "combined offensive power" fallback and should
    only be used when the skill's true damage type is not yet known.
    """

    if skill_damage.total_raw_damage < 0:
        raise ValueError(
            "Skill raw damage cannot be negative."
        )

    event = DDDamageEvent(
        base_value=skill_damage.total_raw_damage,
        scaling_coefficient=0.0,
        damage_type=damage_type,
        can_crit=can_crit,
    )

    damage = calculate_dd_damage(
        event,
        stats,
        mitigation=mitigation,
    )

    return SkillCombatDamageResult(
        skill_rank_id=skill_damage.skill_rank_id,
        damage_type=damage_type,
        raw_skill_damage=skill_damage.total_raw_damage,
        damage=damage,
    )
