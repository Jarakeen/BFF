from minmax.build import Build
from minmax.calculation import StatEngine
from minmax.calculation_context import CalculationContext
from minmax.effects import EffectOperation
from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId


DESCRIPTION = (
    "(5 items) Increases your Critical Damage and Healing by 8%. "
    "Increases your Critical Damage and Healing by an additional "
    "16% when you are Sneaking or Invisible."
)


def bonus(description: str) -> GearSetBonus:
    return GearSetBonus(
        id=1,
        set_id=23,
        piece_count=5,
        description=description,
    )


def test_archers_mind_resolves_unconditional_and_conditional_effects():
    effects = GearSetEffectResolver().resolve(
        bonus(DESCRIPTION)
    )

    assert [
        (
            effect.stat,
            effect.operation,
            effect.value,
            effect.condition,
        )
        for effect in effects
    ] == [
        (
            StatId.CRITICAL_DAMAGE,
            EffectOperation.ADD_PERCENT,
            8.0,
            None,
        ),
        (
            StatId.HEALING_DONE,
            EffectOperation.ADD_PERCENT,
            8.0,
            None,
        ),
        (
            StatId.CRITICAL_DAMAGE,
            EffectOperation.ADD_PERCENT,
            16.0,
            "sneaking_or_invisible",
        ),
        (
            StatId.HEALING_DONE,
            EffectOperation.ADD_PERCENT,
            16.0,
            "sneaking_or_invisible",
        ),
    ]


def test_archers_mind_base_bonus_applies_when_condition_false():
    effects = GearSetEffectResolver().resolve(
        bonus(DESCRIPTION)
    )

    build = Build(
        base_stats={
            StatId.CRITICAL_DAMAGE.value: 100,
            StatId.HEALING_DONE.value: 100,
        },
        effects=effects,
    )

    result = StatEngine().calculate(
        build,
        CalculationContext(
            conditions={
                "sneaking_or_invisible": False,
            }
        ),
    )

    assert result.value(StatId.CRITICAL_DAMAGE) == 108
    assert result.value(StatId.HEALING_DONE) == 108


def test_archers_mind_conditional_bonus_applies_when_condition_true():
    effects = GearSetEffectResolver().resolve(
        bonus(DESCRIPTION)
    )

    build = Build(
        base_stats={
            StatId.CRITICAL_DAMAGE.value: 100,
            StatId.HEALING_DONE.value: 100,
        },
        effects=effects,
    )

    result = StatEngine().calculate(
        build,
        CalculationContext(
            conditions={
                "sneaking_or_invisible": True,
            }
        ),
    )

    assert result.value(StatId.CRITICAL_DAMAGE) == 124
    assert result.value(StatId.HEALING_DONE) == 124