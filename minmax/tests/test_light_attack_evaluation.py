import pytest

from minmax.build_evaluation import BuildEvaluation
from minmax.calculation import CalculationResult, StatBreakdown
from minmax.combat_contribution import CombatContribution
from minmax.light_attack_evaluation import (
    resolve_light_attack_from_evaluation,
)
from minmax.stat_ids import StatId


def make_evaluation():
    stats = CalculationResult(
        stats={
            StatId.MAX_MAGICKA: StatBreakdown(base=30000),
            StatId.MAX_STAMINA: StatBreakdown(base=15000),
            StatId.SPELL_DAMAGE: StatBreakdown(base=5000),
            StatId.WEAPON_DAMAGE: StatBreakdown(base=4000),
        }
    )

    contributions = (
        CombatContribution(
            source="Test LA",
            effect_type="flame_damage_done",
            raw_value=0.05,
            uptime=1.0,
            effective_value=0.05,
        ),
        CombatContribution(
            source="Test Direct",
            effect_type="direct_damage_done",
            raw_value=0.10,
            uptime=1.0,
            effective_value=0.10,
        ),
        CombatContribution(
            source="Test Single Target",
            effect_type="single_target_damage_done",
            raw_value=0.08,
            uptime=0.5,
            effective_value=0.04,
        ),
        CombatContribution(
            source="Test Global",
            effect_type="damage_done",
            raw_value=0.05,
            uptime=1.0,
            effective_value=0.05,
        ),
    )

    return BuildEvaluation(
        stats=stats,
        combat_effects=(),
        combat_contributions=contributions,
    )


def test_light_attack_state_comes_from_build_evaluation():
    evaluation = make_evaluation()

    state = resolve_light_attack_from_evaluation(
        evaluation=evaluation,
    )

    assert state.magicka == 30000
    assert state.stamina == 15000

    assert state.la_flame_spell_damage == 5000
    assert state.la_flame_weapon_damage == 4000

    assert state.flame_damage_done == pytest.approx(0.05)
    assert state.direct_damage_done == pytest.approx(0.10)
    assert state.single_target_damage_done == pytest.approx(0.04)
    assert state.damage_done == pytest.approx(0.05)