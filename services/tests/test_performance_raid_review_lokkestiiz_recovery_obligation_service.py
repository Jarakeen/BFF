from services.performance_raid_review_landing_recovery_service import RaidReviewRecoveryActor
from services.performance_raid_review_lokkestiiz_recovery_obligation_service import (
    PerformanceRaidReviewLokkestiizRecoveryObligationService,
)
from services.rotation_lokkestiiz_landing_clock_service import EncounterObservedClockBoundary


def _landing(seconds: float, occurrence: int = 1) -> EncounterObservedClockBoundary:
    return EncounterObservedClockBoundary(
        encounter_id="lokkestiiz",
        fact_key="aerial_onslaught_flight",
        boundary="end",
        occurrence=occurrence,
        time_seconds=seconds,
        source="reviewed runtime evidence",
    )


def test_reviewed_signals_keep_horn_debuff_brittle_and_dd_reacquisition_separate() -> None:
    signals = PerformanceRaidReviewLokkestiizRecoveryObligationService.reviewed_signals()
    keys = {signal.semantic_key for signal in signals}

    assert keys == {
        "aggressive_horn_after_landing",
        "elemental_susceptibility_after_landing",
        "major_brittle_after_landing",
        "boss_damage_reacquisition_after_landing",
    }


def test_healer_obligations_are_measured_independently() -> None:
    result = PerformanceRaidReviewLokkestiizRecoveryObligationService().measure(
        report_code="A",
        fight_id=1,
        fight_start_time_ms=0.0,
        landing_boundaries=[_landing(50.0)],
        actors=[RaidReviewRecoveryActor(11, "Magrat", "Healer", "magrat")],
        boss_actor_id=99,
        events=[
            {"timestamp": 50600.0, "type": "cast", "sourceID": 11, "abilityName": "Aggressive Horn"},
            {"timestamp": 51200.0, "type": "cast", "sourceID": 11, "abilityName": "Elemental Susceptibility"},
            {"timestamp": 53400.0, "type": "applydebuff", "sourceID": 11, "targetID": 99, "abilityName": "Major Brittle"},
        ],
    )

    by_key = {row.signal_semantic_key: row for row in result.observations}
    assert by_key["aggressive_horn_after_landing"].delay_seconds == 0.6
    assert by_key["elemental_susceptibility_after_landing"].delay_seconds == 1.2
    assert by_key["major_brittle_after_landing"].delay_seconds == 3.4


def test_immediate_horn_does_not_hide_late_brittle() -> None:
    result = PerformanceRaidReviewLokkestiizRecoveryObligationService().measure(
        report_code="A",
        fight_id=1,
        fight_start_time_ms=0.0,
        landing_boundaries=[_landing(70.0)],
        actors=[RaidReviewRecoveryActor(11, "Magrat", "Healer", "magrat")],
        boss_actor_id=99,
        events=[
            {"timestamp": 70100.0, "type": "cast", "sourceID": 11, "abilityName": "Aggressive Horn"},
            {"timestamp": 70200.0, "type": "cast", "sourceID": 11, "abilityName": "Elemental Susceptibility"},
            {"timestamp": 74800.0, "type": "refreshdebuff", "sourceID": 11, "targetID": 99, "abilityName": "Major Brittle"},
        ],
    )

    by_key = {row.signal_semantic_key: row for row in result.observations}
    assert by_key["aggressive_horn_after_landing"].delay_seconds == 0.1
    assert by_key["major_brittle_after_landing"].delay_seconds == 4.8


def test_dd_reacquisition_requires_positive_damage_to_boss() -> None:
    result = PerformanceRaidReviewLokkestiizRecoveryObligationService().measure(
        report_code="A",
        fight_id=2,
        fight_start_time_ms=0.0,
        landing_boundaries=[_landing(40.0)],
        actors=[RaidReviewRecoveryActor(7, "DD One", "DPS", "dd-one")],
        boss_actor_id=99,
        events=[
            {"timestamp": 40100.0, "type": "damage", "sourceID": 7, "targetID": 88, "amount": 9000},
            {"timestamp": 40200.0, "type": "damage", "sourceID": 7, "targetID": 99, "amount": 0},
            {"timestamp": 41100.0, "type": "damage", "sourceID": 7, "targetID": 99, "amount": 12000},
        ],
    )

    assert len(result.observations) == 1
    obs = result.observations[0]
    assert obs.signal_semantic_key == "boss_damage_reacquisition_after_landing"
    assert obs.delay_seconds == 1.1


def test_missing_specific_healer_obligation_stays_unresolved_without_blocking_others() -> None:
    result = PerformanceRaidReviewLokkestiizRecoveryObligationService().measure(
        report_code="A",
        fight_id=3,
        fight_start_time_ms=0.0,
        landing_boundaries=[_landing(60.0)],
        actors=[RaidReviewRecoveryActor(11, "Magrat", "Healer", "magrat")],
        boss_actor_id=99,
        events=[
            {"timestamp": 60500.0, "type": "cast", "sourceID": 11, "abilityName": "Aggressive Horn"},
            {"timestamp": 60700.0, "type": "cast", "sourceID": 11, "abilityName": "Elemental Susceptibility"},
        ],
    )

    keys = {row.signal_semantic_key for row in result.observations}
    assert "aggressive_horn_after_landing" in keys
    assert "elemental_susceptibility_after_landing" in keys
    assert "major_brittle_after_landing" not in keys
    assert any("Major Brittle" in message for message in result.unresolved)


def test_numeric_ability_ids_cannot_satisfy_named_healer_obligations() -> None:
    result = PerformanceRaidReviewLokkestiizRecoveryObligationService().measure(
        report_code="A",
        fight_id=4,
        fight_start_time_ms=0.0,
        landing_boundaries=[_landing(30.0)],
        actors=[RaidReviewRecoveryActor(11, "Magrat", "Healer", "magrat")],
        boss_actor_id=99,
        events=[
            {"timestamp": 30100.0, "type": "cast", "sourceID": 11, "abilityGameID": 46537},
            {"timestamp": 30200.0, "type": "applydebuff", "sourceID": 11, "targetID": 99, "abilityGameID": 12345},
        ],
    )

    assert result.observations == ()
    assert len(result.unresolved) == 3
