from services.performance_raid_review_dd_ground_continuity_service import (
    PerformanceRaidReviewDDGroundContinuityService,
)
from services.performance_raid_review_landing_recovery_service import RaidReviewRecoveryActor
from services.performance_raid_review_mechanic_window_service import RaidReviewEncounterWindow


def _dd(actor_id=7, label="DD One"):
    return RaidReviewRecoveryActor(actor_id, label, "DPS", label.casefold().replace(" ", "-"))


def _damage(seconds, *, source=7, target=99, amount=1000):
    return {
        "timestamp": seconds * 1000.0,
        "type": "damage",
        "sourceID": source,
        "targetID": target,
        "amount": amount,
    }


def _flight(start, end):
    return RaidReviewEncounterWindow(
        report_code="A",
        fight_id=1,
        semantic_key="aerial_onslaught_flight_1",
        label="Aerial Onslaught Flight 1",
        start_seconds=start,
        end_seconds=end,
        evidence_source="reviewed flight evidence",
        reviewed=True,
    )


def test_long_ground_gap_is_measured_between_positive_boss_hits() -> None:
    result = PerformanceRaidReviewDDGroundContinuityService().measure(
        report_code="A",
        fight_id=1,
        fight_start_time_ms=0.0,
        fight_end_time_ms=20_000.0,
        events=[_damage(1.0), _damage(2.0), _damage(8.0), _damage(9.0)],
        boss_actor_id=99,
        actors=[_dd()],
        inactivity_threshold_seconds=3.0,
    )

    assert result.unresolved == ()
    obs = result.observations[0]
    assert obs.damage_event_count == 4
    assert obs.measured_gap_count == 3
    assert obs.inactivity_gap_count == 1
    assert obs.inactivity_windows == ((2.0, 8.0),)
    assert obs.total_inactivity_seconds == 6.0
    assert obs.longest_inactivity_seconds == 6.0


def test_reviewed_flight_window_splits_ground_segments_and_is_not_scored_as_dd_silence() -> None:
    result = PerformanceRaidReviewDDGroundContinuityService().measure(
        report_code="A",
        fight_id=1,
        fight_start_time_ms=0.0,
        fight_end_time_ms=80_000.0,
        events=[_damage(2.0), _damage(4.0), _damage(61.0), _damage(62.0)],
        boss_actor_id=99,
        actors=[_dd()],
        excluded_mechanic_windows=[_flight(5.0, 60.0)],
        inactivity_threshold_seconds=3.0,
    )

    obs = result.observations[0]
    assert obs.measured_gap_count == 2
    assert obs.inactivity_gap_count == 0
    assert obs.total_inactivity_seconds == 0.0
    assert obs.longest_inactivity_seconds == 0.0


def test_leading_and_trailing_eligible_time_are_not_inferred_as_player_inactivity() -> None:
    result = PerformanceRaidReviewDDGroundContinuityService().measure(
        report_code="A",
        fight_id=1,
        fight_start_time_ms=0.0,
        fight_end_time_ms=20_000.0,
        events=[_damage(8.0), _damage(9.0)],
        boss_actor_id=99,
        actors=[_dd()],
        inactivity_threshold_seconds=3.0,
    )

    obs = result.observations[0]
    assert obs.measured_gap_count == 1
    assert obs.inactivity_gap_count == 0
    assert obs.inactivity_windows == ()


def test_wrong_target_zero_damage_and_other_actor_do_not_create_continuity_evidence() -> None:
    result = PerformanceRaidReviewDDGroundContinuityService().measure(
        report_code="A",
        fight_id=1,
        fight_start_time_ms=0.0,
        fight_end_time_ms=20_000.0,
        events=[
            _damage(1.0),
            _damage(2.0, target=55),
            _damage(3.0, amount=0),
            _damage(4.0, source=8),
            _damage(5.0),
        ],
        boss_actor_id=99,
        actors=[_dd()],
        inactivity_threshold_seconds=3.0,
    )

    obs = result.observations[0]
    assert obs.damage_event_count == 2
    assert obs.measured_gap_count == 1
    assert obs.inactivity_gap_count == 1
    assert obs.inactivity_windows == ((1.0, 5.0),)


def test_fewer_than_two_hits_in_same_eligible_segment_stays_unresolved() -> None:
    result = PerformanceRaidReviewDDGroundContinuityService().measure(
        report_code="A",
        fight_id=1,
        fight_start_time_ms=0.0,
        fight_end_time_ms=80_000.0,
        events=[_damage(4.0), _damage(61.0)],
        boss_actor_id=99,
        actors=[_dd()],
        excluded_mechanic_windows=[_flight(5.0, 60.0)],
        inactivity_threshold_seconds=3.0,
    )

    assert result.observations == ()
    assert any("fewer than two positive boss-damage events" in message for message in result.unresolved)


def test_non_dd_actors_are_not_measured() -> None:
    result = PerformanceRaidReviewDDGroundContinuityService().measure(
        report_code="A",
        fight_id=1,
        fight_start_time_ms=0.0,
        fight_end_time_ms=20_000.0,
        events=[_damage(1.0), _damage(10.0)],
        boss_actor_id=99,
        actors=[RaidReviewRecoveryActor(7, "Healer", "Healer", "healer")],
        inactivity_threshold_seconds=3.0,
    )

    assert result.observations == ()
    assert result.unresolved == ("No DPS actors were supplied for ground-continuity analysis.",)
