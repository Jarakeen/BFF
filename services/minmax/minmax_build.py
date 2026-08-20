from services.minmax.build import Build
from services.minmax.calculation import StatEngine
from services.minmax.effects import Effect, EffectOperation
from services.minmax.stat_ids import StatId


build = Build(
    name="Health Test",
    base_stats={
        StatId.MAX_HEALTH.value: 10_000,
    },
)

build.add_effect(
    Effect(
        stat=StatId.MAX_HEALTH,
        operation=EffectOperation.ADD,
        value=954,
        source="Glyph of Health",
    )
)

build.add_effect(
    Effect(
        stat=StatId.MAX_HEALTH,
        operation=EffectOperation.ADD,
        value=954,
        source="Glyph of Health #1",
    )
)

build.add_effect(
    Effect(
        stat=StatId.MAX_HEALTH,
        operation=EffectOperation.ADD,
        value=954,
        source="Glyph of Health #2",
    )
)

build.add_effect(
    Effect(
        stat=StatId.WEAPON_DAMAGE,
        operation=EffectOperation.ADD,
        value=348,
        source="Glyph of Weapon Damage",
    )
)

build.add_effect(
    Effect(
        stat=StatId.WEAPON_DAMAGE,
        operation=EffectOperation.ADD_PERCENT,
        value=11,
        source="Potent Nirncrux",
    )
)


breakdown = result.stats[StatId.MAX_HEALTH]

print("Base:", breakdown.base)
print("Additive:", breakdown.additive)
print("Final:", breakdown.final)

for source in breakdown.sources:
    print(
        source.source,
        source.operation,
        source.value,
    )

    
base_stats={
    StatId.WEAPON_DAMAGE.value: 1000,
}

engine = StatEngine()

result = engine.calculate(build)

print(
    "Maximum Health:",
    result.value(StatId.MAX_HEALTH)
)