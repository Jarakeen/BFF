from __future__ import annotations

from minmax.runtime_effect_window import RuntimeEffectActiveWindow
from models.combat_simulation import (
    CombatSimulationCombatant,
    CombatSimulationEvent,
    CombatSimulationResourceResult,
    CombatSimulationResult,
    CombatSimulationTargetState,
    SimulationEventPriority,
)
from services.combat_simulation_snapshot_service import CombatSimulationSnapshotService


def _result() -> CombatSimulationResult:
    return CombatSimulationResult(
        duration_seconds=12.0,
        initial_bar="front",
        final_bar="back",
        events=(
            CombatSimulationEvent(
                time_seconds=0.0,
                priority=int(SimulationEventPriority.ACTION),
                sequence=0,
                event_type="action",
                source="Combat Prayer",
                payload=(
                    ("kind", "skill"),
                    ("bar", "front"),
                    ("target_key", ""),
                ),
            ),
            CombatSimulationEvent(
                time_seconds=0.0,
                priority=int(SimulationEventPriority.RESOURCE_COST),
                sequence=0,
                event_type="action_cost",
                source="Combat Prayer",
                payload=(
                    ("resource", "magicka"),
                    ("before", 30000),
                    ("attempted_change", -3000),
                    ("applied_change", -3000),
                    ("after", 27000),
                    ("shortfall", 0),
                    ("wasted_restore", 0),
                ),
            ),
            CombatSimulationEvent(
                time_seconds=2.0,
                priority=int(SimulationEventPriority.ACTION),
                sequence=0,
                event_type="action",
                source="bar_swap",
                payload=(
                    ("kind", "bar_swap"),
                    ("bar", "back"),
                    ("target_key", ""),
                ),
            ),
            CombatSimulationEvent(
                time_seconds=2.0,
                priority=int(SimulationEventPriority.RESOURCE_RESTORE),
                sequence=0,
                event_type="recovery_tick",
                source="In-combat recovery tick",
                payload=(
                    ("resource", "magicka"),
                    ("before", 27000),
                    ("attempted_change", 1600),
                    ("applied_change", 1600),
                    ("after", 28600),
                    ("shortfall", 0),
                    ("wasted_restore", 0),
                ),
            ),
        ),
        resources=(
            CombatSimulationResourceResult(
                resource="magicka",
                starting_amount=30000,
                ending_amount=28600,
            ),
        ),
        effect_windows=(
            RuntimeEffectActiveWindow(
                effect_name="minor_resolve",
                source="Combat Prayer",
                start_time_seconds=0.0,
                end_time_seconds=10.0,
                target="group",
                sequence=0,
                magnitude=2974.0,
            ),
        ),
        target_state=CombatSimulationTargetState(
            combatants=(
                CombatSimulationCombatant("Magrat", "self"),
                CombatSimulationCombatant("Tank 1", "ally"),
            ),
        ),
        unresolved=("exact group recipients unresolved",),
    )


def test_snapshot_projects_exact_resource_and_bar_state() -> None:
    service = CombatSimulationSnapshotService()

    early = service.snapshot_at(_result(), time_seconds=1.0)
    assert early.active_bar == "front"
    assert [(item.resource, item.current_amount) for item in early.resources] == [
        ("magicka", 27000),
    ]

    at_swap = service.snapshot_at(_result(), time_seconds=2.0)
    assert at_swap.active_bar == "back"
    assert [(item.resource, item.current_amount) for item in at_swap.resources] == [
        ("magicka", 28600),
    ]


def test_snapshot_projects_active_effect_window_without_recomputing_it() -> None:
    service = CombatSimulationSnapshotService()

    active = service.snapshot_at(_result(), time_seconds=9.999)
    assert [window.effect_name for window in active.active_effect_windows] == [
        "minor_resolve",
    ]
    assert active.active_effect_windows[0].magnitude == 2974.0
    assert active.active_effect_windows[0].target == "group"

    expired = service.snapshot_at(_result(), time_seconds=10.0)
    assert expired.active_effect_windows == ()


def test_snapshot_preserves_simulation_unresolved_boundaries() -> None:
    snapshot = CombatSimulationSnapshotService().snapshot_at(
        _result(),
        time_seconds=5.0,
    )

    assert snapshot.unresolved == ("exact group recipients unresolved",)


def test_snapshot_rejects_time_outside_simulation_horizon() -> None:
    service = CombatSimulationSnapshotService()

    for instant in (-0.1, 12.1):
        try:
            service.snapshot_at(_result(), time_seconds=instant)
        except ValueError as exc:
            assert "snapshot time" in str(exc)
        else:
            raise AssertionError("Expected out-of-range snapshot time to fail closed")



def test_snapshot_preserves_explicit_target_state() -> None:
    snapshot = CombatSimulationSnapshotService().snapshot_at(
        _result(),
        time_seconds=5.0,
    )

    assert snapshot.target_state is not None
    assert [item.identity for item in snapshot.target_state.combatants] == [
        "Magrat",
        "Tank 1",
    ]



def test_snapshot_projects_health_after_bound_heal_changes() -> None:
    from dataclasses import replace

    base = _result()
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Tank 1",
                "ally",
                current_health=20000,
                maximum_health=25000,
            ),
        ),
    )
    health_change = CombatSimulationEvent(
        time_seconds=3.0,
        priority=int(SimulationEventPriority.DIRECT_RESULT),
        sequence=0,
        event_type="health_change",
        source="Combat Prayer",
        payload=(
            ("recipient", "Tank 1"),
            ("before", 20000),
            ("attempted_heal", 4000.0),
            ("applied_heal", 4000.0),
            ("overheal", 0.0),
            ("after", 24000),
            ("maximum_health", 25000),
            ("origin_event_type", "direct_heal"),
        ),
    )
    result = replace(
        base,
        events=tuple(sorted((*base.events, health_change))),
        target_state=state,
    )

    before = CombatSimulationSnapshotService().snapshot_at(
        result,
        time_seconds=2.5,
    )
    after = CombatSimulationSnapshotService().snapshot_at(
        result,
        time_seconds=3.0,
    )

    assert [(item.identity, item.current_health, item.maximum_health) for item in before.health] == [
        ("Tank 1", 20000, 25000),
    ]
    assert [(item.identity, item.current_health, item.maximum_health) for item in after.health] == [
        ("Tank 1", 24000, 25000),
    ]



def test_snapshot_projects_health_after_incoming_damage() -> None:
    from dataclasses import replace

    base = _result()
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Tank 1",
                "ally",
                current_health=20000,
                maximum_health=25000,
            ),
        ),
    )
    damage_change = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.DIRECT_RESULT),
        sequence=0,
        event_type="health_change",
        source="Boss Cleave",
        payload=(
            ("recipient", "Tank 1"),
            ("before", 20000),
            ("attempted_damage", 6000.0),
            ("applied_damage", 6000.0),
            ("overkill", 0.0),
            ("after", 14000),
            ("maximum_health", 25000),
            ("origin_event_type", "incoming_damage"),
        ),
    )
    result = replace(
        base,
        events=tuple(sorted((*base.events, damage_change))),
        target_state=state,
    )

    snapshot = CombatSimulationSnapshotService().snapshot_at(
        result,
        time_seconds=1.0,
    )

    assert [(item.identity, item.current_health, item.maximum_health) for item in snapshot.health] == [
        ("Tank 1", 14000, 25000),
    ]
