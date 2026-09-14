import pytest

from minmax.champion_point_static_repository import ChampionPointRecord
from services.extreme_recovery_champion_point_branch_service import (
    ExtremeRecoveryChampionPointBranchKind,
    ExtremeRecoveryChampionPointBranchService,
)


def _record(name: str, description: str, *, max_points: int = 50, jump_points=(10, 20, 30, 40, 50)):
    return ChampionPointRecord(
        name=name,
        skill_type=1,
        max_points=max_points,
        jump_points=tuple(jump_points),
        description=description,
        discipline_index=2,
    )


def test_enlivening_overflow_applies_to_magicka_recovery_with_shared_cap():
    row = ExtremeRecoveryChampionPointBranchService.classify(
        _record(
            "Enlivening Overflow",
            "While overhealing yourself or an ally, you grant them Health, Magicka, and Stamina Recovery equal to 0.5% of your Max Magicka, up to a cap of 150.",
        ),
        "magicka_recovery",
    )

    assert row.complete
    assert row.kind is ExtremeRecoveryChampionPointBranchKind.CAPPED_DYNAMIC_FLAT
    assert row.flat_ceiling == pytest.approx(150.0)
    assert "Max Magicka" in row.condition


def test_strategic_reserve_is_health_only():
    record = _record(
        "Strategic Reserve",
        "Gain 30 Health Recovery for every 10 Ultimate you have.",
    )
    health = ExtremeRecoveryChampionPointBranchService.classify(record, "health_recovery")
    magicka = ExtremeRecoveryChampionPointBranchService.classify(record, "magicka_recovery")

    assert health.complete
    assert health.kind is ExtremeRecoveryChampionPointBranchKind.ULTIMATE_SCALED_FLAT
    assert magicka.complete is False
    assert magicka.kind is ExtremeRecoveryChampionPointBranchKind.UNRESOLVED


def test_shared_per_stage_recovery_applies_to_magicka():
    row = ExtremeRecoveryChampionPointBranchService.classify(
        _record(
            "Rejuvenation",
            "Grants 18 Health, Magicka, and Stamina Recovery per stage.",
            max_points=50,
            jump_points=(10, 20, 30, 40, 50),
        ),
        "magicka_recovery",
    )

    assert row.complete
    assert row.kind is ExtremeRecoveryChampionPointBranchKind.PER_STAGE_FLAT
    assert row.stages == 5
    assert row.flat_ceiling == pytest.approx(90.0)


def test_conditional_paired_per_stage_recovery_keeps_runtime_condition():
    row = ExtremeRecoveryChampionPointBranchService.classify(
        _record(
            "Refreshing Stride",
            "While Sprinting you gain 100 Health and Magicka Recovery per stage.",
            max_points=5,
            jump_points=(),
        ),
        "health_recovery",
    )

    assert row.complete
    assert row.kind is ExtremeRecoveryChampionPointBranchKind.PER_STAGE_FLAT
    assert row.stages == 5
    assert row.flat_ceiling == pytest.approx(500.0)
    assert row.condition == "while Sprinting"


def test_conditional_recovery_by_value_per_stage_applies_to_magicka():
    row = ExtremeRecoveryChampionPointBranchService.classify(
        _record(
            "Peace of Mind",
            "Increases Magicka and Health Recovery while under the effects of Crowd Control Immunity by 40 per stage.",
            max_points=50,
            jump_points=(10, 20, 30, 40, 50),
        ),
        "magicka_recovery",
    )

    assert row.complete
    assert row.kind is ExtremeRecoveryChampionPointBranchKind.PER_STAGE_FLAT
    assert row.stages == 5
    assert row.flat_ceiling == pytest.approx(200.0)
    assert row.condition == "while under Crowd Control Immunity"


def test_shared_recovery_by_value_per_stage_applies_to_magicka():
    row = ExtremeRecoveryChampionPointBranchService.classify(
        _record(
            "Sustained by Suffering",
            "Increases your Health, Magicka, and Stamina Recovery by 30 per stage while under the effects of a negative effect.",
            max_points=5,
            jump_points=(),
        ),
        "magicka_recovery",
    )

    assert row.complete
    assert row.kind is ExtremeRecoveryChampionPointBranchKind.PER_STAGE_FLAT
    assert row.stages == 5
    assert row.flat_ceiling == pytest.approx(150.0)
    assert row.condition == "while under a negative effect"


def test_recovery_used_only_as_input_is_not_objective_relevant():
    text = (
        "Healing yourself or an ally under 50% Health grants them Minor Heroism for 1 second "
        "for every 300 Magicka Recovery you have."
    )

    assert not ExtremeRecoveryChampionPointBranchService.mentions_objective_recovery(
        text,
        "magicka_recovery",
    )


def test_unknown_objective_fails_closed():
    with pytest.raises(KeyError):
        ExtremeRecoveryChampionPointBranchService.classify(
            _record("Mystery", "Grants 10 Magicka Recovery per stage."),
            "spell_damage",
        )
