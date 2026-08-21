import pytest

from minmax.build import Build
from minmax.dd_single_build_evaluator import (
    DDBuildEvaluation,
    DDBuildEvaluator,
)
from minmax.dd_damage import DDDamageEvent
from minmax.effects import (
    Effect,
    EffectOperation,
)
from minmax.evaluation_context import EvaluationContext
from minmax.stat_ids import StatId


def test_empty_build_can_be_evaluated_as_dd_build():
    result = DDBuildEvaluator().evaluate(
        Build(),
        DDDamageEvent(
            base_value=1000,
        ),
    )

    assert isinstance(result, DDBuildEvaluation)
    assert result.dd_stats.weapon_damage == 0
    assert result.dd_stats.spell_damage == 0
    assert result.damage.expected_damage == 1000
    assert result.damage.mitigated_damage == 1000


def test_weapon_damage_reaches_dd_damage_calculation():
    build = Build(
        base_stats={
            StatId.WEAPON_DAMAGE.value: 2000,
        }
    )

    result = DDBuildEvaluator().evaluate(
        build,
        DDDamageEvent(
            base_value=1000,
            scaling_coefficient=0.5,
            damage_type="physical",
        ),
    )

    assert result.dd_stats.weapon_damage == 2000
    assert result.damage.offensive_stat == "weapon_damage"
    assert result.damage.offensive_power == 2000
    assert result.damage.scaled_damage == 2000


def test_spell_damage_reaches_magical_damage_calculation():
    build = Build(
        base_stats={
            StatId.SPELL_DAMAGE.value: 3000,
        }
    )

    result = DDBuildEvaluator().evaluate(
        build,
        DDDamageEvent(
            base_value=1000,
            scaling_coefficient=0.5,
            damage_type="flame",
        ),
    )

    assert result.dd_stats.spell_damage == 3000
    assert result.damage.offensive_stat == "spell_damage"
    assert result.damage.offensive_power == 3000
    assert result.damage.scaled_damage == 2500


def test_stat_effect_changes_dd_damage():
    build = Build(
        base_stats={
            StatId.WEAPON_DAMAGE.value: 1000,
        }
    )

    build.add_effect(
        Effect(
            operation=EffectOperation.ADD,
            value=500,
            source="Test Weapon Damage",
            stat=StatId.WEAPON_DAMAGE,
        )
    )

    result = DDBuildEvaluator().evaluate(
        build,
        DDDamageEvent(
            base_value=1000,
            scaling_coefficient=0.5,
            damage_type="physical",
        ),
    )

    assert result.dd_stats.weapon_damage == 1500
    assert result.damage.scaled_damage == 1750


def test_physical_penetration_reaches_mitigation():
    build = Build(
        base_stats={
            StatId.PHYSICAL_PENETRATION.value: 10000,
        }
    )

    context = EvaluationContext(
        target_resistance=18200,
    )

    result = DDBuildEvaluator().evaluate(
        build,
        DDDamageEvent(
            base_value=1000,
            damage_type="physical",
            can_crit=False,
        ),
        context,
    )

    assert result.damage.penetration_stat == (
    "physical_penetration"
    )
    assert result.damage.penetration == 10000
    assert result.damage.mitigation_multiplier == pytest.approx(
        0.836
    )
    assert result.damage.mitigated_damage == pytest.approx(
        836
    )


def test_spell_penetration_reaches_mitigation():
    build = Build(
        base_stats={
            StatId.SPELL_PENETRATION.value: 10000,
        }
    )

    context = EvaluationContext(
        target_resistance=18200,
    )

    result = DDBuildEvaluator().evaluate(
        build,
        DDDamageEvent(
            base_value=1000,
            damage_type="flame",
            can_crit=False,
        ),
        context,
    )

    assert result.damage.penetration_stat == (
        "spell_penetration"
    )
    assert result.damage.penetration == 10000
    assert result.damage.mitigation_multiplier == pytest.approx(
    0.836
    )
    assert result.damage.mitigated_damage == pytest.approx(
    836
    )

def test_penetration_is_capped_at_target_resistance():
    build = Build(
        base_stats={
            StatId.PHYSICAL_PENETRATION.value: 20000,
        }
    )

    context = EvaluationContext(
        target_resistance=18200,
    )

    result = DDBuildEvaluator().evaluate(
        build,
        DDDamageEvent(
            base_value=1000,
            damage_type="physical",
            can_crit=False,
        ),
        context,
    )

    assert result.dd_stats.effective_physical_penetration == 18200
    assert result.dd_stats.physical_overpenetration == 1800
    assert result.damage.penetration == 18200
    assert result.damage.mitigation_multiplier == 1.0
    assert result.damage.mitigated_damage == 1000


def test_critical_stats_reach_dd_damage():
    build = Build(
        base_stats={
            StatId.CRITICAL_CHANCE.value: 50,
            StatId.CRITICAL_DAMAGE.value: 100,
        }
    )

    result = DDBuildEvaluator().evaluate(
        build,
        DDDamageEvent(
            base_value=1000,
        ),
    )

    assert result.damage.critical_chance == 0.5
    assert result.damage.critical_damage == 1.0
    assert result.damage.expected_damage == 1500


def test_target_resistance_is_optional():
    result = DDBuildEvaluator().evaluate(
        Build(),
        DDDamageEvent(
            base_value=1000,
            damage_type="physical",
            can_crit=False,
        ),
    )

    assert result.damage.penetration == 0
    assert result.damage.mitigation_multiplier == 1.0
    assert result.damage.mitigated_damage == 1000


def test_target_resistance_is_applied_when_present():
    context = EvaluationContext(
        target_resistance=18200,
    )

    result = DDBuildEvaluator().evaluate(
        Build(),
        DDDamageEvent(
            base_value=1000,
            damage_type="physical",
            can_crit=False,
        ),
        context,
    )

    assert result.damage.penetration == 0
    assert result.damage.mitigation_multiplier == 0.636
    assert result.damage.mitigated_damage == 636