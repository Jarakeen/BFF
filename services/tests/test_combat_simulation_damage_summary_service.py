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
    assert [(row.source, row.event_count, row.attempted_damage) for row in summary.damage_by_source] == [
        ("Skill A", 2, 5000.0),
        ("Skill B", 1, 1000.0),
    ]


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
