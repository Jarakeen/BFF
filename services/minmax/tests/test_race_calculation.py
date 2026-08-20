from pathlib import Path

from services.minmax.build import Build
from services.minmax.build_effect_service import BuildEffectService
from services.minmax.calculation import StatEngine
from services.minmax.gear_set_effect_resolver import GearSetEffectResolver
from services.minmax.gear_set_effect_service import GearSetEffectService
from services.minmax.gear_set_repository import GearSetRepository
from services.minmax.race_effect_service import RaceEffectService
from services.minmax.race_repository import RaceRepository
from services.minmax.stat_ids import StatId


DB_PATH = Path("data/eso.db")

ALTMER_ID = 1
AKAVIRI_DRAGONGUARD_ID = 21


def stat_engine() -> StatEngine:
    gear_set_service = GearSetEffectService(
        repository=GearSetRepository(DB_PATH),
        resolver=GearSetEffectResolver(),
    )

    race_effect_service = RaceEffectService(
        repository=RaceRepository(DB_PATH),
    )

    build_effect_service = BuildEffectService(
        gear_set_effect_service=gear_set_service,
        race_effect_service=race_effect_service,
    )

    return StatEngine(
        build_effect_service=build_effect_service,
    )


def test_race_is_included_in_build_calculation():
    build = Build(
        name="Altmer Test",
        base_stats={
            StatId.MAX_MAGICKA.value: 10_000,
            StatId.SPELL_DAMAGE.value: 1_000,
            StatId.WEAPON_DAMAGE.value: 1_000,
        },
    )

    build.set_race(ALTMER_ID)

    result = stat_engine().calculate(build)

    assert result.value(StatId.MAX_MAGICKA) == 12_000
    assert result.value(StatId.SPELL_DAMAGE) == 1_258
    assert result.value(StatId.WEAPON_DAMAGE) == 1_258


def test_race_and_gear_effects_combine():
    build = Build(
        name="Altmer + Akaviri Test",
        base_stats={
            StatId.MAX_MAGICKA.value: 10_000,
            StatId.SPELL_DAMAGE.value: 1_000,
            StatId.WEAPON_DAMAGE.value: 1_000,
            StatId.MAX_HEALTH.value: 10_000,
        },
    )

    build.set_race(ALTMER_ID)
    build.add_gear_set(
        AKAVIRI_DRAGONGUARD_ID,
        4,
    )

    result = stat_engine().calculate(build)

    assert result.value(StatId.MAX_MAGICKA) == 12_000
    assert result.value(StatId.SPELL_DAMAGE) == 1_258
    assert result.value(StatId.WEAPON_DAMAGE) == 1_258
    assert result.value(StatId.MAX_HEALTH) == 11_206


def test_racial_effects_do_not_mutate_build():
    build = Build(
        name="Race Mutation Test",
        base_stats={
            StatId.MAX_MAGICKA.value: 10_000,
        },
    )

    build.set_race(ALTMER_ID)

    assert build.effects == []

    stat_engine().calculate(build)

    assert build.effects == []