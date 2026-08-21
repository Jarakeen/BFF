from minmax.calculation import (
    CalculationResult,
    StatBreakdown,
)
from minmax.evaluation_context import EvaluationContext
from minmax.dd_stat_evaluation import (
    evaluate_dd_stats,
)


def make_calculation(**values):
    stats = {
        key: StatBreakdown(base=value)
        for key, value in values.items()
    }

    return CalculationResult(stats=stats)


def test_weapon_and_spell_damage_are_preserved():
    calculation = make_calculation(
        weapon_damage=5000,
        spell_damage=4500,
    )

    result = evaluate_dd_stats(
        calculation,
        EvaluationContext(),
    )

    assert result.weapon_damage == 5000
    assert result.spell_damage == 4500


def test_penetration_is_capped_by_target_resistance():
    calculation = make_calculation(
        physical_penetration=20000,
        spell_penetration=19000,
    )

    result = evaluate_dd_stats(
        calculation,
        EvaluationContext(
            target_resistance=18200,
        ),
    )

    assert result.effective_physical_penetration == 18200
    assert result.effective_spell_penetration == 18200


def test_overpenetration_is_exposed():
    calculation = make_calculation(
        physical_penetration=20000,
        spell_penetration=19000,
    )

    result = evaluate_dd_stats(
        calculation,
        EvaluationContext(
            target_resistance=18200,
        ),
    )

    assert result.physical_overpenetration == 1800
    assert result.spell_overpenetration == 800


def test_crit_chance_is_capped():
    calculation = make_calculation(
        critical_chance=110,
    )

    result = evaluate_dd_stats(
        calculation,
        EvaluationContext(),
    )

    assert result.effective_critical_chance == 100
    assert result.critical_chance_excess == 10


def test_crit_damage_is_capped():
    calculation = make_calculation(
        critical_damage=140,
    )

    result = evaluate_dd_stats(
        calculation,
        EvaluationContext(),
    )

    assert result.effective_critical_damage == 125
    assert result.critical_damage_excess == 15


def test_penetration_is_not_capped_without_target_resistance():
    calculation = make_calculation(
        physical_penetration=20000,
    )

    result = evaluate_dd_stats(
        calculation,
        EvaluationContext(),
    )

    assert result.effective_physical_penetration == 20000
    assert result.physical_overpenetration == 0