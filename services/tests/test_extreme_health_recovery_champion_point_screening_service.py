from minmax.champion_point_static_repository import ChampionPointRecord
from services.extreme_health_recovery_champion_point_screening_service import (
    ExtremeHealthRecoveryChampionPointScreeningService,
    ExtremeHealthRecoveryChampionPointScreeningStatus,
)


def _record(name: str, description: str, *, slottable: bool = True) -> ChampionPointRecord:
    return ChampionPointRecord(
        name=name,
        skill_type=1 if slottable else 0,
        max_points=50,
        jump_points=(),
        description=description,
    )


def test_retains_direct_health_recovery_reference():
    row = ExtremeHealthRecoveryChampionPointScreeningService.screen(
        _record(
            "Strategic Reserve",
            "Gain 30 Health Recovery for every 10 Ultimate you have.",
        )
    )

    assert row.status is ExtremeHealthRecoveryChampionPointScreeningStatus.RELEVANT
    assert row.relevant is True


def test_retains_shared_triple_recovery_reference():
    row = ExtremeHealthRecoveryChampionPointScreeningService.screen(
        _record(
            "Sustained by Suffering",
            "Increases your Health, Magicka, and Stamina Recovery by 30 per stage while under the effects of a negative effect.",
        )
    )

    assert row.status is ExtremeHealthRecoveryChampionPointScreeningStatus.RELEVANT


def test_prunes_magicka_recovery_only_reference():
    row = ExtremeHealthRecoveryChampionPointScreeningService.screen(
        _record(
            "Hope Infusion",
            "Healing yourself or an ally under 50% Health grants them Minor Heroism for 1 second for every 300 Magicka Recovery you have.",
        )
    )

    assert row.status is ExtremeHealthRecoveryChampionPointScreeningStatus.IRRELEVANT


def test_prunes_ultimate_generation_without_direct_recovery():
    row = ExtremeHealthRecoveryChampionPointScreeningService.screen(
        _record(
            "Last Stand",
            "When you take damage below 20% Health you gain Major Heroism, granting 3 Ultimate every 1.5 seconds for 9 seconds.",
        )
    )

    assert row.status is ExtremeHealthRecoveryChampionPointScreeningStatus.IRRELEVANT


def test_prunes_food_duration_without_magnitude_change():
    row = ExtremeHealthRecoveryChampionPointScreeningService.screen(
        _record(
            "Rationer",
            "Adds 10 minutes to the duration of any food or drink that increases your character's stats per stage.",
            slottable=False,
        )
    )

    assert row.status is ExtremeHealthRecoveryChampionPointScreeningStatus.IRRELEVANT
