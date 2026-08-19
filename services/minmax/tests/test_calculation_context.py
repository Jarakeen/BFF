from services.minmax.build import Build
from services.minmax.calculation import StatEngine
from services.minmax.calculation_context import CalculationContext
from services.minmax.effects import Effect, EffectOperation
from services.minmax.stat_ids import StatId


def make_effect(*, value: float, condition: str | None = None) -> Effect:
    return Effect(
        stat=StatId.MAX_HEALTH,
        operation=EffectOperation.ADD,
        value=value,
        source="test",
        condition=condition,
    )


def test_unconditional_effect_applies():
    build = Build(
        base_stats={"max_health": 1000},
        effects=[make_effect(value=500)],
    )

    result = StatEngine().calculate(build)

    assert result.value(StatId.MAX_HEALTH) == 1500


def test_condition_true_applies_effect():
    build = Build(
        base_stats={"max_health": 1000},
        effects=[
            make_effect(
                value=500,
                condition="sneaking",
            )
        ],
    )

    context = CalculationContext(
        conditions={"sneaking": True}
    )

    result = StatEngine().calculate(build, context)

    assert result.value(StatId.MAX_HEALTH) == 1500


def test_condition_false_skips_effect():
    build = Build(
        base_stats={"max_health": 1000},
        effects=[
            make_effect(
                value=500,
                condition="sneaking",
            )
        ],
    )

    context = CalculationContext(
        conditions={"sneaking": False}
    )

    result = StatEngine().calculate(build, context)

    assert result.value(StatId.MAX_HEALTH) == 1000


def test_missing_condition_defaults_to_false():
    build = Build(
        base_stats={"max_health": 1000},
        effects=[
            make_effect(
                value=500,
                condition="sneaking",
            )
        ],
    )

    context = CalculationContext()

    result = StatEngine().calculate(build, context)

    assert result.value(StatId.MAX_HEALTH) == 1000


def test_no_context_skips_conditional_effect():
    build = Build(
        base_stats={"max_health": 1000},
        effects=[
            make_effect(
                value=500,
                condition="sneaking",
            )
        ],
    )

    result = StatEngine().calculate(build)

    assert result.value(StatId.MAX_HEALTH) == 1000