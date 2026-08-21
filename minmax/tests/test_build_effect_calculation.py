from pathlib import Path

from minmax.build import Build
from minmax.build_effect_service import BuildEffectService
from minmax.calculation import StatEngine
from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_set_effect_service import GearSetEffectService
from minmax.gear_set_repository import GearSetRepository
from minmax.stat_ids import StatId


DB_PATH = Path("data/eso.db")

AKAVIRI_DRAGONGUARD_ID = 21


def stat_engine() -> StatEngine:
    repository = GearSetRepository(DB_PATH)

    gear_set_service = GearSetEffectService(
        repository=repository,
        resolver=GearSetEffectResolver(),
    )

    build_effect_service = BuildEffectService(
        gear_set_effect_service=gear_set_service,
    )

    return StatEngine(
        build_effect_service=build_effect_service,
    )


def test_stat_engine_automatically_resolves_build_gear():
    build = Build(
        name="Akaviri Integration Test",
        base_stats={
            StatId.MAX_HEALTH.value: 10_000,
            StatId.MAGICKA_RECOVERY.value: 0,
            StatId.HEALING_TAKEN.value: 100,
        },
    )

    build.add_gear_set(
        AKAVIRI_DRAGONGUARD_ID,
        4,
    )

    result = stat_engine().calculate(build)

    assert result.value(StatId.MAX_HEALTH) == 11_206
    assert result.value(StatId.MAGICKA_RECOVERY) == 129
    assert result.value(StatId.HEALING_TAKEN) == 104


def test_stat_engine_does_not_mutate_build_effects():
    build = Build(
        name="Mutation Test",
        base_stats={
            StatId.MAX_HEALTH.value: 10_000,
        },
    )

    build.add_gear_set(
        AKAVIRI_DRAGONGUARD_ID,
        4,
    )

    assert build.effects == []

    stat_engine().calculate(build)

    assert build.effects == []