from services.performance_raid_review_landing_recovery_service import RaidReviewRecoveryActor
from services.performance_raid_review_lokkestiiz_pull_service import (
    PerformanceRaidReviewLokkestiizPullService,
)


def _flight_events(*, include_landing: bool = True):
    events = [
        {"timestamp": 20000.0, "type": "cast", "abilityGameID": 122820},
        {"timestamp": 21000.0, "type": "damage", "targetID": 99, "amount": 1000},
    ]
    if include_landing:
        events.extend(
            [
                {"timestamp": 72000.0, "type": "damage", "sourceID": 7, "targetID": 99, "amount": 2000},
                {"timestamp": 72600.0, "type": "cast", "sourceID": 11, "abilityName": "Aggressive Horn"},
                {"timestamp": 72900.0, "type": "cast", "sourceID": 11, "abilityName": "Elemental Susceptibility"},
                {"timestamp": 74100.0, "type": "applydebuff", "sourceID": 11, "targetID": 99, "abilityName": "Major Brittle"},
                {"timestamp": 73300.0, "type": "damage", "sourceID": 7, "targetID": 99, "amount": 5000},
            ]
        )
    return events


def test_complete_pull_builds_boundaries_windows_and_recovery_observations() -> None:
    result = PerformanceRaidReviewLokkestiizPullService().build(
        report_code="A",
        fight_id=22,
        fight_start_time_ms=0.0,
        events=_flight_events(),
        boss_actor_id=99,
        actors=[
            RaidReviewRecoveryActor(11, "Magrat", "Healer", "magrat"),
            RaidReviewRecoveryActor(7, "DD One", "DPS", "dd-one"),
        ],
        evidence_source="ESO Logs report A fight 22",
    )

    assert [(item.boundary, item.occurrence, item.time_seconds) for item in result.boundaries] == [
        ("begin", 1, 20.0),
        ("end", 1, 72.0),
    ]
    assert len(result.mechanic_windows) == 1
    window = result.mechanic_windows[0]
    assert window.semantic_key == "aerial_onslaught_flight_1"
    assert window.start_seconds == 20.0
    assert window.end_seconds == 72.0

    by_key = {row.signal_semantic_key: row for row in result.recovery_observations}
    assert by_key["aggressive_horn_after_landing"].delay_seconds == 0.6
    assert by_key["elemental_susceptibility_after_landing"].delay_seconds == 0.9
    assert by_key["major_brittle_after_landing"].delay_seconds == 2.1
    assert by_key["boss_damage_reacquisition_after_landing"].delay_seconds == 0.0
    assert result.unresolved == ()


def test_wipe_without_landing_preserves_unresolved_and_does_not_invent_recovery() -> None:
    result = PerformanceRaidReviewLokkestiizPullService().build(
        report_code="A",
        fight_id=23,
        fight_start_time_ms=0.0,
        events=_flight_events(include_landing=False),
        boss_actor_id=99,
        actors=[RaidReviewRecoveryActor(11, "Magrat", "Healer", "magrat")],
        evidence_source="ESO Logs report A fight 23",
    )

    assert [(item.boundary, item.occurrence) for item in result.boundaries] == [("begin", 1)]
    assert result.mechanic_windows == ()
    assert result.recovery_observations == ()
    assert any("No qualifying boss-damage resumption" in message for message in result.unresolved)
    assert any("requires exactly one observed begin and one observed end" in message for message in result.unresolved)


def test_missing_actors_does_not_block_mechanic_evidence() -> None:
    result = PerformanceRaidReviewLokkestiizPullService().build(
        report_code="A",
        fight_id=24,
        fight_start_time_ms=0.0,
        events=_flight_events(),
        boss_actor_id=99,
        actors=[],
        evidence_source="ESO Logs report A fight 24",
    )

    assert len(result.mechanic_windows) == 1
    assert result.recovery_observations == ()
    assert any("No raid actors were supplied" in message for message in result.unresolved)


def test_boundary_detector_remains_source_of_numeric_signature_translation() -> None:
    result = PerformanceRaidReviewLokkestiizPullService().build(
        report_code="A",
        fight_id=25,
        fight_start_time_ms=0.0,
        events=[
            {"timestamp": 20000.0, "type": "cast", "abilityGameID": 999999},
            {"timestamp": 21000.0, "type": "damage", "targetID": 99, "amount": 1000},
            {"timestamp": 72000.0, "type": "damage", "targetID": 99, "amount": 1000},
        ],
        boss_actor_id=99,
        actors=[],
        evidence_source="ESO Logs report A fight 25",
    )

    assert result.boundaries == ()
    assert result.mechanic_windows == ()
    assert any("No reviewed Lokkestiiz flight-entry evidence signatures" in message for message in result.unresolved)
