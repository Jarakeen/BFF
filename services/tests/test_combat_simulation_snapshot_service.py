from __future__ import annotations

from minmax.runtime_effect_window import RuntimeEffectActiveWindow
from models.combat_simulation import (
    CombatSimulationEvent,
    CombatSimulationResourceResult,
    CombatSimulationResult,
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
