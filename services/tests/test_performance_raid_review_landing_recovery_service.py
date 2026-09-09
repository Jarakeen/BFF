from services.performance_raid_review_landing_recovery_service import (
    PerformanceRaidReviewLandingRecoveryService,
    RaidReviewRecoveryActor,
    RaidReviewRecoverySignal,
)
from services.rotation_lokkestiiz_landing_clock_service import EncounterObservedClockBoundary


def _landing(seconds: float, occurrence: int = 1):
    return EncounterObservedClockBoundary(
        encounter_id="lokkestiiz",
        fact_key="aerial_onslaught_flight",
        boundary="end",
        occurrence=occurrence,
        time_seconds=seconds,
        source="reviewed runtime",
    )


def test_dd_reacquisition_uses_first_positive_boss_damage_after_landing() -> None:
    service = PerformanceRaidReviewLandingRecoveryService()
    result = service.measure(
        report_code="A",
        fight_id=1,
        fight_start_time_ms=1000.0,
        landing_boundaries=[_landing(70.0)],
        actors=[RaidReviewRecoveryActor(7, "DD One", "DPS", "dd-one")],
        signals=[
            RaidReviewRecoverySignal(
                "boss_damage_reacquired",
                "Boss Damage Reacquired",
                "DPS",
                ("damage", "calculateddamage"),
                require_boss_target=True,
            )
        ],
        boss_actor_id=99,
        events=[
            {"timestamp": 71500.0, "type": "damage", "sourceID": 7, "targetID": 98, "amount": 4000},
            {"timestamp": 72000.0, "type": "damage", "sourceID": 7, "targetID": 99, "amount": 0},
            {"timestamp": 72750.0, "type": "damage", "sourceID": 7, "targetID": 99, "amount": 5000},
        ],
    )

    assert result.unresolved == ()
    assert len(result.observations) == 1
    assert result.observations[0].delay_seconds == 1.75
    assert result.observations[0].signal_semantic_key == "boss_damage_reacquired"


def test_healer_recovery_uses_reviewed_translated_ability_name() -> None:
    service = PerformanceRaidReviewLandingRecoveryService()
    result = service.measure(
        report_code="A",
        fight_id=1,
        fight_start_time_ms=0.0,
        landing_boundaries=[_landing(50.0)],
        actors=[RaidReviewRecoveryActor(11, "Magrat", "Healer", "magrat")],
        signals=[
            RaidReviewRecoverySignal(
                "landing_support_reapplication",
                "Landing Support Reapplication",
                "Healer",
                ("cast", "applydebuff"),
                ability_names=("Aggressive Horn", "Elemental Susceptibility"),
            )
        ],
        events=[
            {"timestamp": 50400.0, "type": "cast", "sourceID": 11, "abilityName": "Combat Prayer"},
            {"timestamp": 50900.0, "type": "cast", "sourceID": 11, "abilityName": "Aggressive Horn"},
        ],
    )

    assert result.unresolved == ()
    obs = result.observations[0]
    assert obs.delay_seconds == 0.9
    assert obs.evidence_ability_name == "Aggressive Horn"


def test_tank_recovery_can_require_reviewed_named_action() -> None:
    service = PerformanceRaidReviewLandingRecoveryService()
    result = service.measure(
        report_code="A",
        fight_id=2,
        fight_start_time_ms=0.0,
        landing_boundaries=[_landing(40.0)],
        actors=[RaidReviewRecoveryActor(3, "Tank", "Tank", "tank")],
        signals=[
            RaidReviewRecoverySignal(
                "boss_control_reestablished",
                "Boss Control Re-established",
                "Tank",
                ("cast",),
                ability_names=("Pierce Armor",),
            )
        ],
        events=[
            {"timestamp": 41800.0, "type": "cast", "sourceID": 3, "abilityName": "Pierce Armor"},
        ],
    )

    assert result.observations[0].delay_seconds == 1.8
    assert result.observations[0].role == "Tank"


def test_missing_recovery_evidence_stays_unresolved() -> None:
    service = PerformanceRaidReviewLandingRecoveryService()
    result = service.measure(
        report_code="A",
        fight_id=1,
        fight_start_time_ms=0.0,
        landing_boundaries=[_landing(70.0)],
        actors=[RaidReviewRecoveryActor(7, "DD One", "DPS")],
        signals=[
            RaidReviewRecoverySignal(
                "boss_damage_reacquired",
                "Boss Damage Reacquired",
                "DPS",
                ("damage",),
                require_boss_target=True,
            )
        ],
        boss_actor_id=99,
        max_delay_seconds=5.0,
        events=[
            {"timestamp": 80000.0, "type": "damage", "sourceID": 7, "targetID": 99, "amount": 5000},
        ],
    )

    assert result.observations == ()
    assert "No reviewed DPS recovery evidence" in result.unresolved[0]


def test_numeric_ability_id_alone_cannot_satisfy_named_recovery_signal() -> None:
    service = PerformanceRaidReviewLandingRecoveryService()
    result = service.measure(
        report_code="A",
        fight_id=1,
        fight_start_time_ms=0.0,
        landing_boundaries=[_landing(50.0)],
        actors=[RaidReviewRecoveryActor(11, "Magrat", "Healer")],
        signals=[
            RaidReviewRecoverySignal(
                "horn_after_landing",
                "Horn After Landing",
                "Healer",
                ("cast",),
                ability_names=("Aggressive Horn",),
            )
        ],
        events=[
            {"timestamp": 50500.0, "type": "cast", "sourceID": 11, "abilityGameID": 46537},
        ],
    )

    assert result.observations == ()
    assert result.unresolved
