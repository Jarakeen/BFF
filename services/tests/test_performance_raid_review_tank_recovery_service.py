from services.performance_raid_review_landing_recovery_service import (
    RaidReviewRecoveryActor,
    RaidReviewRecoverySignal,
)
from services.performance_raid_review_tank_recovery_service import (
    PerformanceRaidReviewTankRecoveryService,
)
from services.rotation_lokkestiiz_landing_clock_service import EncounterObservedClockBoundary


def _landing(occurrence: int, seconds: float) -> EncounterObservedClockBoundary:
    return EncounterObservedClockBoundary(
        encounter_id="lokkestiiz",
        fact_key="aerial_onslaught_flight",
        boundary="end",
        occurrence=occurrence,
        time_seconds=seconds,
        source="reviewed test landing",
    )


def _signal(key: str, label: str, ability: str) -> RaidReviewRecoverySignal:
    return RaidReviewRecoverySignal(
        semantic_key=key,
        label=label,
        role="Tank",
        event_types=("cast", "applydebuff", "refreshdebuff"),
        ability_names=(ability,),
    )


def test_measures_distinct_tank_obligations_independently() -> None:
    result = PerformanceRaidReviewTankRecoveryService().measure(
        report_code="A",
        fight_id=1,
        fight_start_time_ms=0.0,
        events=(
            {"timestamp": 60500.0, "type": "cast", "sourceID": 5, "abilityName": "Pierce Armor"},
            {"timestamp": 62100.0, "type": "applydebuff", "sourceID": 5, "abilityName": "Turning Tide"},
        ),
        landing_boundaries=(_landing(1, 60.0),),
        actors=(RaidReviewRecoveryActor(5, "Tank One", "Tank", "tank-one"),),
        signals=(
            _signal("boss_control_after_landing", "Boss Control", "Pierce Armor"),
            _signal("support_debuff_after_landing", "Support Debuff", "Turning Tide"),
        ),
        boss_actor_id=99,
    )

    assert [(row.signal_semantic_key, row.delay_seconds) for row in result.observations] == [
        ("boss_control_after_landing", 0.5),
        ("support_debuff_after_landing", 2.1),
    ]
    assert len(result.opportunities) == 2


def test_missing_tank_obligation_remains_an_explicit_opportunity_and_unresolved() -> None:
    result = PerformanceRaidReviewTankRecoveryService().measure(
        report_code="A",
        fight_id=2,
        fight_start_time_ms=0.0,
        events=({"timestamp": 60500.0, "type": "cast", "sourceID": 5, "abilityName": "Pierce Armor"},),
        landing_boundaries=(_landing(1, 60.0),),
        actors=(RaidReviewRecoveryActor(5, "Tank One", "Tank", "tank-one"),),
        signals=(
            _signal("boss_control_after_landing", "Boss Control", "Pierce Armor"),
            _signal("support_debuff_after_landing", "Support Debuff", "Turning Tide"),
        ),
        boss_actor_id=99,
    )

    keys = {row.signal_semantic_key for row in result.observations}
    assert keys == {"boss_control_after_landing"}
    assert {row.signal_semantic_key for row in result.opportunities} == {
        "boss_control_after_landing",
        "support_debuff_after_landing",
    }
    assert any("Support Debuff" in message for message in result.unresolved)


def test_non_tank_actors_do_not_receive_tank_obligations() -> None:
    result = PerformanceRaidReviewTankRecoveryService().measure(
        report_code="A",
        fight_id=3,
        fight_start_time_ms=0.0,
        events=(),
        landing_boundaries=(_landing(1, 60.0),),
        actors=(RaidReviewRecoveryActor(7, "DD One", "DPS", "dd-one"),),
        signals=(_signal("boss_control_after_landing", "Boss Control", "Pierce Armor"),),
        boss_actor_id=99,
    )

    assert result.observations == ()
    assert result.opportunities == ()
    assert result.unresolved == ("No Tank actors were supplied for tank recovery.",)


def test_numeric_ability_id_alone_cannot_satisfy_named_tank_obligation() -> None:
    result = PerformanceRaidReviewTankRecoveryService().measure(
        report_code="A",
        fight_id=4,
        fight_start_time_ms=0.0,
        events=({"timestamp": 60500.0, "type": "cast", "sourceID": 5, "abilityGameID": 12345},),
        landing_boundaries=(_landing(1, 60.0),),
        actors=(RaidReviewRecoveryActor(5, "Tank One", "Tank", "tank-one"),),
        signals=(_signal("boss_control_after_landing", "Boss Control", "Pierce Armor"),),
        boss_actor_id=99,
    )

    assert result.observations == ()
    assert len(result.opportunities) == 1
    assert any("Boss Control" in message for message in result.unresolved)


def test_unreviewed_or_non_tank_signals_are_not_promoted_into_tank_truth() -> None:
    result = PerformanceRaidReviewTankRecoveryService().measure(
        report_code="A",
        fight_id=5,
        fight_start_time_ms=0.0,
        events=(),
        landing_boundaries=(_landing(1, 60.0),),
        actors=(RaidReviewRecoveryActor(5, "Tank One", "Tank", "tank-one"),),
        signals=(
            RaidReviewRecoverySignal(
                semantic_key="draft_control",
                label="Draft Control",
                role="Tank",
                event_types=("cast",),
                ability_names=("Pierce Armor",),
                reviewed=False,
            ),
            RaidReviewRecoverySignal(
                semantic_key="healer_signal",
                label="Healer Signal",
                role="Healer",
                event_types=("cast",),
                ability_names=("Aggressive Horn",),
            ),
        ),
        boss_actor_id=99,
    )

    assert result.observations == ()
    assert result.opportunities == ()
    assert result.unresolved == ("No reviewed Tank recovery signals were supplied.",)
