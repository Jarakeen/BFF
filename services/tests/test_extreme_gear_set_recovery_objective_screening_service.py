from services.extreme_gear_set_recovery_objective_screening_service import (
    ExtremeGearSetRecoveryObjectiveScreeningService,
)


def test_health_recovery_screen_prunes_unrelated_damage_proc():
    report = ExtremeGearSetRecoveryObjectiveScreeningService.review(
        "When you deal damage, deal 1000 Flame Damage to nearby enemies.",
        "health_recovery",
    )

    assert report.proven_irrelevant
    assert report.blockers == ()


def test_health_recovery_screen_retains_direct_health_recovery():
    report = ExtremeGearSetRecoveryObjectiveScreeningService.review(
        "While under 60% Health, your Health Recovery is increased by 800.",
        "health_recovery",
    )

    assert not report.proven_irrelevant
    assert "Health Recovery reference" in report.recovery_hazards


def test_health_recovery_screen_retains_shared_recovery_list():
    report = ExtremeGearSetRecoveryObjectiveScreeningService.review(
        "Gain 465 Health, Magicka, and Stamina Recovery for 10 seconds.",
        "health_recovery",
    )

    assert not report.proven_irrelevant
    assert report.recovery_hazards


def test_health_recovery_screen_retains_fortitude_buff():
    report = ExtremeGearSetRecoveryObjectiveScreeningService.review(
        "Gain Minor Fortitude while in combat.",
        "health_recovery",
    )

    assert not report.proven_irrelevant
    assert "Minor Fortitude recovery modifier" in report.recovery_hazards


def test_other_recovery_stat_can_prune_health_only_bonus():
    report = ExtremeGearSetRecoveryObjectiveScreeningService.review(
        "Increase your Health Recovery by 800.",
        "magicka_recovery",
    )

    assert report.proven_irrelevant
