from models.combat_simulation import (
    CombatSimulationCombatant,
    CombatSimulationEvent,
    CombatSimulationResult,
    CombatSimulationTargetState,
)
from services.combat_simulation_damage_summary_service import (
    CombatSimulationDamageSummaryService,
)


def _event(time, sequence, event_type, source, **payload):
    return CombatSimulationEvent(
        time_seconds=time,
        priority=40,
        sequence=sequence,
        event_type=event_type,
        source=source,
        payload=tuple(payload.items()),
    )


def test_damage_summary_totals_target_damage_and_sources() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(
            _event(1.0, 0, "outgoing_damage", "Skill A", recipient="Boss", amount=3000.0),
            _event(
                1.0,
                1,
                "health_change",
                "Skill A",
                recipient="Boss",
                applied_damage=3000.0,
                after=7000,
            ),
            _event(2.0, 0, "outgoing_damage", "Skill A", recipient="Boss", amount=2000.0),
            _event(
                2.0,
                1,
                "health_change",
                "Skill A",
                recipient="Boss",
                applied_damage=2000.0,
                after=5000,
            ),
            _event(3.0, 0, "outgoing_damage", "Skill B", recipient="Boss", amount=1000.0),
            _event(
                3.0,
                1,
                "health_change",
                "Skill B",
                recipient="Boss",
                applied_damage=1000.0,
                after=4000,
            ),
        ),
        unresolved=(),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.outgoing_event_count == 3
    assert summary.attempted_damage == 6000.0
    assert summary.applied_damage == 6000.0
    assert summary.ending_target_health == 4000
    assert summary.target_dead is False
    assert summary.modeled_dps == 1200.0
    assert [
        (
            row.source,
            row.event_count,
            row.attempted_damage,
            row.applied_damage,
            row.overkill,
            row.killing_blow,
        )
        for row in summary.damage_by_source
    ] == [
        ("Skill A", 2, 5000.0, 5000.0, 0.0, False),
        ("Skill B", 1, 1000.0, 1000.0, 0.0, False),
    ]
    assert summary.total_overkill == 0.0
    assert summary.killing_source is None


def test_damage_summary_withholds_dps_when_damage_evidence_is_unresolved() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(),
        unresolved=("DoT runtime anchor unavailable",),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.complete_damage_evidence is False
    assert summary.modeled_dps is None
    assert summary.unresolved == ("DoT runtime anchor unavailable",)



def test_damage_summary_attributes_lethal_overkill_to_killing_source() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=3000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=2.0,
        initial_bar="front",
        final_bar="front",
        events=(
            _event(
                1.0,
                0,
                "outgoing_damage",
                "Execute",
                recipient="Boss",
                amount=8000.0,
            ),
            _event(
                1.0,
                0,
                "health_change",
                "Execute",
                recipient="Boss",
                attempted_damage=8000.0,
                applied_damage=3000.0,
                overkill=5000.0,
                after=0,
                origin_event_type="outgoing_damage",
            ),
            _event(
                1.0,
                0,
                "death",
                "Execute",
                recipient="Boss",
                overkill=5000.0,
                origin_event_type="outgoing_damage",
            ),
        ),
        unresolved=(),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.attempted_damage == 8000.0
    assert summary.applied_damage == 3000.0
    assert summary.total_overkill == 5000.0
    assert summary.target_dead is True
    assert summary.death_time_seconds == 1.0
    assert summary.killing_source == "Execute"
    assert summary.killing_origin_event_type == "outgoing_damage"
    assert summary.modeled_dps == 1500.0
    assert len(summary.damage_by_source) == 1
    row = summary.damage_by_source[0]
    assert row.source == "Execute"
    assert row.attempted_damage == 8000.0
    assert row.applied_damage == 3000.0
    assert row.overkill == 5000.0
    assert row.killing_blow is True


def test_damage_summary_ignores_non_outgoing_health_damage_for_dd_totals() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(
            _event(
                1.0,
                0,
                "health_change",
                "Environmental Hazard",
                recipient="Boss",
                attempted_damage=2000.0,
                applied_damage=2000.0,
                overkill=0.0,
                after=8000,
                origin_event_type="incoming_damage",
            ),
        ),
        unresolved=(),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.attempted_damage == 0.0
    assert summary.applied_damage == 0.0
    assert summary.damage_by_source == ()
    assert summary.killing_source is None
