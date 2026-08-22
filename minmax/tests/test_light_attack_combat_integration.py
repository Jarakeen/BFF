import pytest

from minmax.build_evaluation import BuildEvaluation
from minmax.calculation import CalculationResult, StatBreakdown
from minmax.combat_calculation import calculate_combat_effect
from minmax.combat_context import CombatContext
from minmax.combat_effect_evaluator import CombatEffectEvaluator
from minmax.combat_effects import CombatEffect
from minmax.combat_contribution import calculate_combat_contribution
from minmax.light_attack_evaluation import resolve_light_attack_from_evaluation
from minmax.stat_ids import StatId
from minmax.effects import EffectUnit


def make_base_evaluation(contributions):
    stats = CalculationResult(
        stats={
            StatId.MAX_MAGICKA: StatBreakdown(base=30000),
            StatId.MAX_STAMINA: StatBreakdown(base=15000),
            StatId.SPELL_DAMAGE: StatBreakdown(base=5000),
            StatId.WEAPON_DAMAGE: StatBreakdown(base=4000),
        }
    )

    return BuildEvaluation(
        stats=stats,
        combat_effects=(),
        combat_contributions=tuple(contributions),
    )


def resolve_contribution(effect, *, fight_duration=None):
    context = CombatContext()

    evaluator = CombatEffectEvaluator()

    assert evaluator.is_applicable(effect, context)

    result = calculate_combat_effect(
        effect,
        fight_duration=fight_duration,
    )

    return calculate_combat_contribution(result)


def test_real_combat_effect_flows_into_light_attack_state():
    effect = CombatEffect(
        effect_type="flame_damage_done",
        value=0.05,
        source="Test Flame Modifier",
        unit=EffectUnit.PERCENT,
    )

    contribution = resolve_contribution(effect)

    evaluation = make_base_evaluation(
        [contribution]
    )

    state = resolve_light_attack_from_evaluation(
        evaluation=evaluation,
    )

    assert state.magicka == 30000
    assert state.stamina == 15000
    assert state.la_flame_spell_damage == 5000
    assert state.la_flame_weapon_damage == 4000

    assert state.flame_damage_done == pytest.approx(0.05)


def test_real_uptime_is_preserved_through_light_attack_pipeline():
    effect = CombatEffect(
        effect_type="single_target_damage_done",
        value=0.08,
        source="Test Conditional Modifier",
        unit=EffectUnit.PERCENT,
        duration_value=5,
        duration_unit="seconds",
    )

    contribution = resolve_contribution(
        effect,
        fight_duration=10,
    )

    evaluation = make_base_evaluation(
        [contribution]
    )

    state = resolve_light_attack_from_evaluation(
        evaluation=evaluation,
    )

    assert state.single_target_damage_done == pytest.approx(
        0.04
    )
    
from minmax.light_attack_calculator import (
    calculate_flame_staff_light_attack,
)


def test_real_flame_damage_modifier_changes_final_light_attack_damage():
    baseline_evaluation = make_base_evaluation([])

    baseline_state = resolve_light_attack_from_evaluation(
        evaluation=baseline_evaluation,
    )

    baseline_damage = calculate_flame_staff_light_attack(
        baseline_state,
    )

    flame_effect = CombatEffect(
        effect_type="flame_damage_done",
        value=0.05,
        source="Test Flame Modifier",
        unit=EffectUnit.PERCENT,
    )

    flame_contribution = resolve_contribution(
        flame_effect,
    )

    modified_evaluation = make_base_evaluation(
        [flame_contribution],
    )

    modified_state = resolve_light_attack_from_evaluation(
        evaluation=modified_evaluation,
    )

    modified_damage = calculate_flame_staff_light_attack(
        modified_state,
    )

    assert modified_damage == pytest.approx(
        baseline_damage * 1.05,
    )
    assert modified_damage > baseline_damage    