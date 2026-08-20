from pathlib import Path

from services.minmax.armor_glyph_repository import (
    ArmorGlyphEffectRepository,
)
from services.minmax.build import Build
from services.minmax.build_effect_service import BuildEffectService
from services.minmax.calculation import StatEngine
from services.minmax.gear_set_effect_resolver import GearSetEffectResolver
from services.minmax.gear_set_effect_service import GearSetEffectService
from services.minmax.gear_set_repository import GearSetRepository
from services.minmax.stat_ids import StatId


DB_PATH = Path("data/eso.db")

HEALTH_GLYPH_ID = 26580
PRISMATIC_GLYPH_ID = 68343


def stat_engine() -> StatEngine:
    gear_set_service = GearSetEffectService(
        repository=GearSetRepository(DB_PATH),
        resolver=GearSetEffectResolver(),
    )

    build_effect_service = BuildEffectService(
        gear_set_effect_service=gear_set_service,
        armor_glyph_repository=ArmorGlyphEffectRepository(DB_PATH),
    )

    return StatEngine(
        build_effect_service=build_effect_service,
    )


def test_armor_glyph_is_included_in_build_calculation():
    build = Build(
        name="Armor Glyph Test",
        base_stats={
            StatId.MAX_HEALTH.value: 10_000,
        },
    )

    build.add_armor_glyph(HEALTH_GLYPH_ID)

    result = stat_engine().calculate(build)

    assert result.value(StatId.MAX_HEALTH) == 10_954


def test_prismatic_glyph_contributes_all_three_stats():
    build = Build(
        name="Prismatic Glyph Test",
        base_stats={
            StatId.MAX_HEALTH.value: 10_000,
            StatId.MAX_MAGICKA.value: 10_000,
            StatId.MAX_STAMINA.value: 10_000,
        },
    )

    build.add_armor_glyph(PRISMATIC_GLYPH_ID)

    result = stat_engine().calculate(build)

    assert result.value(StatId.MAX_HEALTH) == 10_477
    assert result.value(StatId.MAX_MAGICKA) == 10_434
    assert result.value(StatId.MAX_STAMINA) == 10_434


def test_armor_glyph_does_not_mutate_build_effects():
    build = Build(
        name="Glyph Mutation Test",
        base_stats={
            StatId.MAX_HEALTH.value: 10_000,
        },
    )

    build.add_armor_glyph(HEALTH_GLYPH_ID)

    assert build.effects == []

    stat_engine().calculate(build)

    assert build.effects == []