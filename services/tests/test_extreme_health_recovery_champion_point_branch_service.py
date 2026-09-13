from minmax.champion_point_static_repository import ChampionPointRecord
from services.extreme_health_recovery_champion_point_branch_service import (
    ExtremeHealthRecoveryChampionPointBranchKind,
    ExtremeHealthRecoveryChampionPointBranchService,
)


def _record(name: str, description: str, *, max_points: int = 5, jumps=()):
    return ChampionPointRecord(
        name=name,
        skill_type=1,
        max_points=max_points,
        jump_points=tuple(jumps),
        description=description,
    )


def test_scores_strategic_reserve_from_canonical_ultimate_cap():
    row = ExtremeHealthRecoveryChampionPointBranchService.classify(
        _record(
            "Strategic Reserve",
            "Gain 30 Health Recovery for every 10 Ultimate you have.",
        )
    )

    assert row.kind is ExtremeHealthRecoveryChampionPointBranchKind.ULTIMATE_SCALED_FLAT
    assert row.flat_ceiling == 1500.0
    assert "500" in str(row.condition)


def test_scores_enlivening_overflow_from_stated_cap():
    row = ExtremeHealthRecoveryChampionPointBranchService.classify(
        _record(
            "Enlivening Overflow",
            "Overhealing yourself or an ally grants them Health, Magicka, and Stamina Recovery equal to .5% of your Max Magicka, up to a cap of 150, for 6 seconds.",
        )
    )

    assert row.kind is ExtremeHealthRecoveryChampionPointBranchKind.CAPPED_DYNAMIC_FLAT
    assert row.flat_ceiling == 150.0
    assert row.condition == "overheal target; Max Magicka high enough to reach stated cap"


def test_scores_peace_of_mind_per_stage():
    row = ExtremeHealthRecoveryChampionPointBranchService.classify(
        _record(
            "Peace of Mind",
            "Increases Magicka and Health Recovery while under the effects of Crowd Control Immunity by 40 per stage.",
            max_points=50,
            jumps=(10, 20, 30, 40, 50),
        )
    )

    assert row.kind is ExtremeHealthRecoveryChampionPointBranchKind.PER_STAGE_FLAT
    assert row.stages == 5
    assert row.flat_ceiling == 200.0
    assert row.condition == "while under Crowd Control Immunity"


def test_scores_refreshing_stride_per_stage():
    row = ExtremeHealthRecoveryChampionPointBranchService.classify(
        _record(
            "Refreshing Stride",
            "While Sprinting you gain 100 Health and Magicka Recovery per stage.",
            max_points=5,
        )
    )

    assert row.kind is ExtremeHealthRecoveryChampionPointBranchKind.PER_STAGE_FLAT
    assert row.flat_ceiling == 500.0


def test_scores_sustained_by_suffering_per_stage():
    row = ExtremeHealthRecoveryChampionPointBranchService.classify(
        _record(
            "Sustained by Suffering",
            "Increases your Health, Magicka, and Stamina Recovery by 30 per stage while under the effects of a negative effect.",
            max_points=5,
        )
    )

    assert row.kind is ExtremeHealthRecoveryChampionPointBranchKind.PER_STAGE_FLAT
    assert row.flat_ceiling == 150.0


def test_unknown_health_recovery_grammar_fails_closed():
    row = ExtremeHealthRecoveryChampionPointBranchService.classify(
        _record("Fixture", "Your Health Recovery changes according to an undocumented rule.")
    )

    assert row.kind is ExtremeHealthRecoveryChampionPointBranchKind.UNRESOLVED
    assert row.flat_ceiling is None
    assert row.unresolved
