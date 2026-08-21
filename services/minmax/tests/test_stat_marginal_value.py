import pytest

from services.minmax.build import Build
from services.minmax.dd_damage import DDDamageEvent
from services.minmax.dd_single_build_evaluator import (
    DDBuildEvaluator,
)
from services.minmax.evaluation_context import EvaluationContext
from services.minmax.stat_ids import StatId
from services.minmax.stat_marginal_value import (
    StatMarginalValue,
    calculate_stat_marginal_value,
)


def test_weapon_damage_marginal_value():
    build = Build(
        base_stats={
            StatId.WEAPON_DAMAGE.value: 1000,
        }
    )

    result = calculate_stat_marginal_value(
        build,
        stat=StatId.WEAPON_DAMAGE,
        delta=100,
        event=DDDamageEvent(
            base_value=1000,
            scaling_coefficient=0.5,
            damage_type="physical",
            can_crit=False,
        ),
    )

    assert isinstance(result, StatMarginalValue)
    assert result.stat == StatId.WEAPON_DAMAGE
    assert result.delta == 100

    assert result.baseline_damage == pytest.approx(
        1500
    )

    assert result.modified_damage == pytest.approx(
        1550
    )

    assert result.absolute_change == pytest.approx(
        50
    )

    assert result.relative_change == pytest.approx(
        50 / 1500
    )

    assert result.value_per_unit == pytest.approx(
        0.5
    )


def test_spell_damage_marginal_value():
    build = Build(
        base_stats={
            StatId.SPELL_DAMAGE.value: 2000,
        }
    )

    result = calculate_stat_marginal_value(
        build,
        stat=StatId.SPELL_DAMAGE,
        delta=100,
        event=DDDamageEvent(
            base_value=1000,
            scaling_coefficient=0.5,
            damage_type="flame",
            can_crit=False,
        ),
    )

    assert result.baseline_damage == pytest.approx(
        2000
    )

    assert result.modified_damage == pytest.approx(
        2050
    )

    assert result.absolute_change == pytest.approx(
        50
    )

    assert result.value_per_unit == pytest.approx(
        0.5
    )


def test_physical_penetration_marginal_value_changes_with_target_resistance():
    build = Build(
        base_stats={
            StatId.PHYSICAL_PENETRATION.value: 5000,
        }
    )

    context = EvaluationContext(
        target_resistance=18200,
    )

    result = calculate_stat_marginal_value(
        build,
        stat=StatId.PHYSICAL_PENETRATION,
        delta=1000,
        event=DDDamageEvent(
            base_value=1000,
            damage_type="physical",
            can_crit=False,
        ),
        context=context,
    )

    assert result.baseline_damage == pytest.approx(
        736
    )

    assert result.modified_damage > (
        result.baseline_damage
    )

    assert result.absolute_change > 0
    assert result.value_per_unit > 0


def test_spell_penetration_marginal_value_uses_spell_penetration():
    build = Build(
        base_stats={
            StatId.SPELL_PENETRATION.value: 5000,
        }
    )

    context = EvaluationContext(
        target_resistance=18200,
    )

    result = calculate_stat_marginal_value(
        build,
        stat=StatId.SPELL_PENETRATION,
        delta=1000,
        event=DDDamageEvent(
            base_value=1000,
            damage_type="flame",
            can_crit=False,
        ),
        context=context,
    )

    assert result.absolute_change > 0
    assert result.modified_damage > (
        result.baseline_damage
    )


def test_penetration_at_cap_has_zero_marginal_value():
    build = Build(
        base_stats={
            StatId.PHYSICAL_PENETRATION.value: 18200,
        }
    )

    context = EvaluationContext(
        target_resistance=18200,
    )

    result = calculate_stat_marginal_value(
        build,
        stat=StatId.PHYSICAL_PENETRATION,
        delta=1000,
        event=DDDamageEvent(
            base_value=1000,
            damage_type="physical",
            can_crit=False,
        ),
        context=context,
    )

    assert result.baseline_damage == pytest.approx(
        1000
    )

    assert result.modified_damage == pytest.approx(
        1000
    )

    assert result.absolute_change == pytest.approx(
        0
    )

    assert result.value_per_unit == pytest.approx(
        0
    )


def test_marginal_value_respects_crit_chance():
    build = Build(
        base_stats={
            StatId.CRITICAL_CHANCE.value: 50,
            StatId.CRITICAL_DAMAGE.value: 100,
        }
    )

    result = calculate_stat_marginal_value(
        build,
        stat=StatId.CRITICAL_CHANCE,
        delta=10,
        event=DDDamageEvent(
            base_value=1000,
        ),
    )

    assert result.baseline_damage == pytest.approx(
        1500
    )

    assert result.modified_damage == pytest.approx(
        1600
    )

    assert result.absolute_change == pytest.approx(
        100
    )


def test_critical_chance_at_cap_has_zero_marginal_value():
    build = Build(
        base_stats={
            StatId.CRITICAL_CHANCE.value: 100,
            StatId.CRITICAL_DAMAGE.value: 100,
        }
    )

    result = calculate_stat_marginal_value(
        build,
        stat=StatId.CRITICAL_CHANCE,
        delta=10,
        event=DDDamageEvent(
            base_value=1000,
        ),
    )

    assert result.absolute_change == pytest.approx(
        0
    )

    assert result.value_per_unit == pytest.approx(
        0
    )


def test_marginal_value_respects_critical_damage():
    build = Build(
        base_stats={
            StatId.CRITICAL_CHANCE.value: 50,
            StatId.CRITICAL_DAMAGE.value: 100,
        }
    )

    result = calculate_stat_marginal_value(
        build,
        stat=StatId.CRITICAL_DAMAGE,
        delta=20,
        event=DDDamageEvent(
            base_value=1000,
        ),
    )

    assert result.baseline_damage == pytest.approx(
        1500
    )

    assert result.modified_damage == pytest.approx(
        1600
    )

    assert result.absolute_change == pytest.approx(
        100
    )


def test_zero_baseline_damage_has_zero_relative_change():
    build = Build()

    result = calculate_stat_marginal_value(
        build,
        stat=StatId.WEAPON_DAMAGE,
        delta=100,
        event=DDDamageEvent(
            base_value=0,
        ),
    )

    assert result.baseline_damage == pytest.approx(
        0
    )

    assert result.relative_change == pytest.approx(
        0
    )


def test_negative_delta_is_rejected():
    build = Build()

    with pytest.raises(ValueError):
        calculate_stat_marginal_value(
            build,
            stat=StatId.WEAPON_DAMAGE,
            delta=-100,
            event=DDDamageEvent(
                base_value=1000,
            ),
        )


def test_zero_delta_is_rejected():
    build = Build()

    with pytest.raises(ValueError):
        calculate_stat_marginal_value(
            build,
            stat=StatId.WEAPON_DAMAGE,
            delta=0,
            event=DDDamageEvent(
                base_value=1000,
            ),
        )


def test_original_build_is_not_modified():
    build = Build(
        base_stats={
            StatId.WEAPON_DAMAGE.value: 1000,
        }
    )

    calculate_stat_marginal_value(
        build,
        stat=StatId.WEAPON_DAMAGE,
        delta=500,
        event=DDDamageEvent(
            base_value=1000,
            scaling_coefficient=0.5,
            damage_type="physical",
            can_crit=False,
        ),
    )

    assert build.base_stats[
        StatId.WEAPON_DAMAGE.value
    ] == 1000


def test_custom_evaluator_is_used():
    class TrackingEvaluator:
        def __init__(self):
            self.calls = 0
            self.delegate = DDBuildEvaluator()

        def evaluate(
            self,
            build,
            event,
            context=None,
        ):
            self.calls += 1

            return self.delegate.evaluate(
                build,
                event,
                context,
            )

    evaluator = TrackingEvaluator()

    calculate_stat_marginal_value(
        Build(),
        stat=StatId.WEAPON_DAMAGE,
        delta=100,
        event=DDDamageEvent(
            base_value=1000,
        ),
        evaluator=evaluator,
    )

    assert evaluator.calls == 2