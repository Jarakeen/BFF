from minmax.build import Build
from minmax.calculation import StatEngine
from minmax.effects import Effect, EffectOperation
from minmax.stat_ids import StatId
from minmax.effects import (
    Effect,
    EffectOperation,
    EffectUnit,
)

def test_base_stat():
    build = Build(
        base_stats={
            StatId.MAX_HEALTH.value: 10_000,
        }
    )

    result = StatEngine().calculate(build)

    assert result.value(StatId.MAX_HEALTH) == 10_000


def test_additive_effect():
    build = Build(
        base_stats={
            StatId.MAX_HEALTH.value: 10_000,
        }
    )

    build.add_effect(
        Effect(
            stat=StatId.MAX_HEALTH,
            operation=EffectOperation.ADD,
            value=954,
            source="Glyph of Health",
        )
    )

    result = StatEngine().calculate(build)

    assert result.value(StatId.MAX_HEALTH) == 10_954


def test_multiple_additive_effects():
    build = Build(
        base_stats={
            StatId.MAX_HEALTH.value: 10_000,
        }
    )

    build.add_effects([
        Effect(
            stat=StatId.MAX_HEALTH,
            operation=EffectOperation.ADD,
            value=954,
            source="Glyph of Health #1",
        ),
        Effect(
            stat=StatId.MAX_HEALTH,
            operation=EffectOperation.ADD,
            value=954,
            source="Glyph of Health #2",
        ),
    ])

    result = StatEngine().calculate(build)

    assert result.value(StatId.MAX_HEALTH) == 11_908


def test_source_breakdown():
    build = Build(
        base_stats={
            StatId.MAX_HEALTH.value: 10_000,
        }
    )

    effect = Effect(
        stat=StatId.MAX_HEALTH,
        operation=EffectOperation.ADD,
        value=954,
        source="Glyph of Health",
    )

    build.add_effect(effect)

    result = StatEngine().calculate(build)

    breakdown = result.stats[StatId.MAX_HEALTH]

    assert breakdown.base == 10_000
    assert breakdown.additive == 954
    assert breakdown.sources == [effect]

def test_stat_engine_ignores_non_stat_effects():
    from minmax.effect_kinds import EffectKind

    build = Build(
        base_stats={
            StatId.MAX_HEALTH.value: 10000,
        },
        effects=[
            Effect(
                kind=EffectKind.COMBAT,
                operation=EffectOperation.ADD,
                value=2534,
                source="Glyph of Frost",
                unit=EffectUnit.FLAT,
                damage_type="frost",
                target="enemy",
            )
        ],
    )

    result = StatEngine().calculate(build)

    assert result.value(StatId.MAX_HEALTH) == 10000    