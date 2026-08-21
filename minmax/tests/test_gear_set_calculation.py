from pathlib import Path

from minmax.build import Build
from minmax.calculation import StatEngine
from minmax.gear_set_effect_service import GearSetEffectService
from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_set_repository import GearSetRepository
from minmax.stat_ids import StatId


DB_PATH = Path("data/eso.db")

AKAVIRI_DRAGONGUARD_ID = 21


def make_build_with_akaviri_dragonguard(
    *,
    equipped_piece_count: int,
) -> Build:
    repository = GearSetRepository(DB_PATH)
    service = GearSetEffectService(
        repository=repository,
        resolver=GearSetEffectResolver(),
    )

    build = Build(
        name="Akaviri Dragonguard Test",
        base_stats={
            StatId.MAX_HEALTH.value: 10_000,
            StatId.MAGICKA_RECOVERY.value: 0,
            StatId.HEALING_TAKEN.value: 100,
        },
    )

    build.add_effects(
        service.resolve_effects(
            AKAVIRI_DRAGONGUARD_ID,
            equipped_piece_count,
        )
    )

    return build


def test_akaviri_dragonguard_four_piece_calculates_stats():
    build = make_build_with_akaviri_dragonguard(
        equipped_piece_count=4,
    )

    result = StatEngine().calculate(build)

    assert result.value(StatId.MAX_HEALTH) == 11_206
    assert result.value(StatId.MAGICKA_RECOVERY) == 129
    assert result.value(StatId.HEALING_TAKEN) == 104


def test_akaviri_dragonguard_calculation_preserves_sources():
    build = make_build_with_akaviri_dragonguard(
        equipped_piece_count=4,
    )

    result = StatEngine().calculate(build)

    health_sources = result.stats[StatId.MAX_HEALTH].sources
    magicka_recovery_sources = result.stats[StatId.MAGICKA_RECOVERY].sources
    healing_taken_sources = result.stats[StatId.HEALING_TAKEN].sources

    assert len(health_sources) == 1
    assert health_sources[0].value == 1206
    assert health_sources[0].source == "Akaviri Dragonguard (4)"

    assert len(magicka_recovery_sources) == 1
    assert magicka_recovery_sources[0].value == 129
    assert magicka_recovery_sources[0].source == "Akaviri Dragonguard (2)"

    assert len(healing_taken_sources) == 1
    assert healing_taken_sources[0].value == 4
    assert healing_taken_sources[0].source == "Akaviri Dragonguard (3)"


def test_akaviri_two_piece_only_applies_two_piece_bonus():
    build = make_build_with_akaviri_dragonguard(
        equipped_piece_count=2,
    )

    result = StatEngine().calculate(build)

    assert result.value(StatId.MAX_HEALTH) == 10_000
    assert result.value(StatId.MAGICKA_RECOVERY) == 129
    assert result.value(StatId.HEALING_TAKEN) == 100