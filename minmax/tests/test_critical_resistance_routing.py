from __future__ import annotations

import pytest

from minmax.dd_stat_evaluation import DDStatEvaluation
from minmax.skill_coefficient import SkillCoefficientResult
from minmax.skill_combat_damage import (
    calculate_classified_skill_combat_damage,
    calculate_skill_combat_damage,
)
from minmax.skill_component_classification import SkillComponentClassification, SkillEffectKind
from minmax.skill_damage import SkillDamageResult


def _stats(*, chance: float = 100.0, crit_damage: float = 50.0) -> DDStatEvaluation:
    return DDStatEvaluation(
        weapon_damage=0.0,
        spell_damage=0.0,
        physical_penetration=0.0,
        spell_penetration=0.0,
        effective_physical_penetration=0.0,
        effective_spell_penetration=0.0,
        physical_overpenetration=0.0,
        spell_overpenetration=0.0,
        critical_chance=chance,
        effective_critical_chance=chance,
        critical_chance_excess=0.0,
        critical_damage=crit_damage,
        effective_critical_damage=crit_damage,
        critical_damage_excess=0.0,
    )


def _aggregate(value: float = 1000.0) -> SkillDamageResult:
    return SkillDamageResult(skill_rank_id=101, components=(), total_raw_damage=value)


def _component(number: int, value: float) -> SkillCoefficientResult:
    return SkillCoefficientResult(
        coefficient_number=number,
        coefficient_type="8",
        max_stat=0.0,
        power=0.0,
        a=0.0,
        b=0.0,
        c=value,
        raw_value=value,
        scaled_value=value,
    )


def test_target_critical_resistance_reduces_expected_critical_damage_before_mitigation():
    result = calculate_skill_combat_damage(
        _aggregate(),
        _stats(),
        target_critical_resistance=1320.0,
    ).damage

    assert result.critical_resistance.reduction_percent == pytest.approx(20.0)
    assert result.critical_resistance.effective_critical_damage_percent == pytest.approx(30.0)
    assert result.critical_damage == pytest.approx(0.30)
    assert result.expected_damage == pytest.approx(1300.0)
    assert result.final_damage == pytest.approx(1300.0)


def test_excess_critical_resistance_floors_crit_to_normal_hit_not_below_it():
    result = calculate_skill_combat_damage(
        _aggregate(),
        _stats(),
        target_critical_resistance=6600.0,
    ).damage

    assert result.critical_damage == pytest.approx(0.0)
    assert result.expected_damage == pytest.approx(1000.0)


def test_noncrit_event_ignores_critical_damage_even_with_target_resistance():
    result = calculate_skill_combat_damage(
        _aggregate(),
        _stats(crit_damage=125.0),
        can_crit=False,
        target_critical_resistance=1320.0,
    ).damage

    assert result.critical_chance == pytest.approx(0.0)
    assert result.critical_damage == pytest.approx(0.0)
    assert result.expected_damage == pytest.approx(1000.0)


def test_classified_damage_component_receives_target_critical_resistance():
    skill = SkillDamageResult(
        skill_rank_id=777,
        components=(_component(1, 1000.0),),
        total_raw_damage=1000.0,
    )
    classifications = (
        SkillComponentClassification(
            skill_rank_id=777,
            coefficient_number=1,
            effect_kind=SkillEffectKind.DAMAGE,
            damage_type="flame",
            is_dot=False,
            is_aoe=False,
            can_crit=True,
            source="verified fixture",
        ),
    )

    result = calculate_classified_skill_combat_damage(
        skill,
        _stats(),
        classifications,
        target_critical_resistance=1320.0,
    )

    assert result.unresolved == ()
    assert result.components[0].damage.expected_damage == pytest.approx(1300.0)
    assert result.components[0].damage.critical_resistance.target_critical_resistance == pytest.approx(1320.0)
