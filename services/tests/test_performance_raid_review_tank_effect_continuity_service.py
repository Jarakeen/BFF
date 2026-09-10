from minmax.runtime_effect_window import RuntimeEffectActiveWindow
from services.performance_raid_review_landing_recovery_service import RaidReviewRecoveryActor
from services.performance_raid_review_mechanic_window_service import RaidReviewEncounterWindow
from services.performance_raid_review_tank_effect_continuity_service import (
    PerformanceRaidReviewTankEffectContinuityService,
    RaidReviewTankEffectRequirement,
)


def _tank(actor_id: int = 5) -> RaidReviewRecoveryActor:
    return RaidReviewRecoveryActor(actor_id, "Main Tank", "Tank", "main-tank")


def _requirement(actor_id: int = 5) -> RaidReviewTankEffectRequirement:
    return RaidReviewTankEffectRequirement(
        semantic_key="major_breach_assignment",
        label="Major Breach",
        effect_names=("Major Breach",),
        source_actor_id=actor_id,
    )


def _flight(start: float, end: float) -> RaidReviewEncounterWindow:
    return RaidReviewEncounterWindow(
        report_code="A",
        fight_id=1,
        semantic_key="aerial_onslaught_flight_1",
        label="Aerial Onslaught Flight 1",
        start_seconds=start,
        end_seconds=end,
        evidence_source="reviewed",
        reviewed=True,
    )


def _window(start: float, end: float, *, source: str = "esologs:actor:5") -> RuntimeEffectActiveWindow:
    return RuntimeEffectActiveWindow(
        effect_name="Major Breach",
        source=source,
        target="esologs:actor:99",
        start_time_seconds=start,
        end_time_seconds=end,
    )


def test_flight_time_is_removed_from_eligible_coverage_denominator() -> None:
    result = PerformanceRaidReviewTankEffectContinuityService().measure(
        report_code="A",
        fight_id=1,
        fight_duration_seconds=100.0,
        effect_windows=(_window(0.0, 40.0), _window(60.0, 100.0)),
        actors=(_tank(),),
        requirements=(_requirement(),),
        excluded_mechanic_windows=(_flight(40.0, 60.0),),
    )

    row = result.observations[0]
    assert row.eligible_seconds == 80.0
    assert row.covered_seconds == 80.0
    assert row.coverage_percent == 100.0


def test_overlapping_duplicate_effect_windows_do_not_inflate_coverage() -> None:
    result = PerformanceRaidReviewTankEffectContinuityService().measure(
        report_code="A",
        fight_id=1,
        fight_duration_seconds=100.0,
        effect_windows=(_window(0.0, 50.0), _window(25.0, 75.0)),
        actors=(_tank(),),
        requirements=(_requirement(),),
    )

    row = result.observations[0]
    assert row.covered_seconds == 75.0
    assert row.coverage_percent == 75.0


def test_wrong_source_actor_does_not_receive_assignment_credit() -> None:
    result = PerformanceRaidReviewTankEffectContinuityService().measure(
        report_code="A",
        fight_id=1,
        fight_duration_seconds=100.0,
        effect_windows=(_window(0.0, 100.0, source="esologs:actor:6"),),
        actors=(_tank(),),
        requirements=(_requirement(),),
    )

    row = result.observations[0]
    assert row.covered_seconds == 0.0
    assert row.coverage_percent == 0.0


def test_missing_assigned_tank_is_unresolved_not_reassigned() -> None:
    result = PerformanceRaidReviewTankEffectContinuityService().measure(
        report_code="A",
        fight_id=1,
        fight_duration_seconds=100.0,
        effect_windows=(),
        actors=(RaidReviewRecoveryActor(8, "Off Tank", "Tank", "off-tank"),),
        requirements=(_requirement(actor_id=5),),
    )

    assert result.observations == ()
    assert any("assigned tank actor 5" in message for message in result.unresolved)


def test_requirement_must_not_accept_non_tank_actor_with_same_id() -> None:
    result = PerformanceRaidReviewTankEffectContinuityService().measure(
        report_code="A",
        fight_id=1,
        fight_duration_seconds=100.0,
        effect_windows=(_window(0.0, 100.0),),
        actors=(RaidReviewRecoveryActor(5, "DD One", "DPS", "dd-one"),),
        requirements=(_requirement(),),
    )

    assert result.observations == ()
    assert result.unresolved
