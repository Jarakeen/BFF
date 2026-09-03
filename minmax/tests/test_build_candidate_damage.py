from types import SimpleNamespace

from minmax.build_candidate_damage import measure_modeled_damage_potency
from minmax.dd_damage import DDDamageEvent
from minmax.evaluation_context import EvaluationContext
from minmax.stat_ids import StatId


def _context(**overrides):
    values = {
        StatId.WEAPON_DAMAGE: 2000.0,
        StatId.SPELL_DAMAGE: 2000.0,
        StatId.PHYSICAL_PENETRATION: 0.0,
        StatId.SPELL_PENETRATION: 0.0,
        StatId.CRITICAL_CHANCE: 0.5,
        StatId.CRITICAL_DAMAGE: 0.5,
    }
    values.update(overrides)
    return SimpleNamespace(
        core_state=SimpleNamespace(
            derived={
                stat: SimpleNamespace(final_value=value)
                for stat, value in values.items()
            }
        )
    )


def test_measure_damage_uses_canonical_stats_and_explicit_event():
    result = measure_modeled_damage_potency(
        context=_context(),
        event=DDDamageEvent(
            base_value=1000.0,
            scaling_coefficient=1.0,
        ),
        evaluation_context=EvaluationContext(),
    )

    assert result.resolved
    assert result.metric_name == "canonical single-event expected damage"
    assert result.value == 6250.0
    assert result.damage is not None
    assert result.dd_stats is not None
    assert result.dd_stats.weapon_damage == 2000.0
    assert result.damage.offensive_power == 4000.0
    assert result.damage.final_damage == result.value
    assert any("event base=1000" in row for row in result.evidence)
    assert any("final expected damage=6250.000000" in row for row in result.evidence)


def test_measure_damage_applies_explicit_target_resistance_for_typed_event():
    without_resistance = measure_modeled_damage_potency(
        context=_context(),
        event=DDDamageEvent(
            base_value=1000.0,
            scaling_coefficient=1.0,
            damage_type="flame",
        ),
        evaluation_context=EvaluationContext(),
    )
    with_resistance = measure_modeled_damage_potency(
        context=_context(),
        event=DDDamageEvent(
            base_value=1000.0,
            scaling_coefficient=1.0,
            damage_type="flame",
        ),
        evaluation_context=EvaluationContext(target_resistance=18_200.0),
    )

    assert without_resistance.resolved
    assert with_resistance.resolved
    assert with_resistance.value < without_resistance.value
    assert with_resistance.damage is not None
    assert with_resistance.damage.mitigation_multiplier < 1.0


def test_measure_damage_refuses_context_without_core_stats():
    result = measure_modeled_damage_potency(
        context=SimpleNamespace(core_state=None),
        event=DDDamageEvent(base_value=1000.0),
        evaluation_context=EvaluationContext(),
    )

    assert result.value is None
    assert not result.resolved
    assert result.unresolved == (
        "Canonical static context has no resolved core stat state.",
    )
