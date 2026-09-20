from __future__ import annotations

from models.combat_simulation import (
    CombatSimulationCombatant,
    CombatSimulationEvent,
    CombatSimulationRecipientBinding,
    CombatSimulationTargetState,
    SimulationEventPriority,
)
from services.combat_simulation_health_service import CombatSimulationHealthService


def _heal_event(
    *,
    time_seconds=1.0,
    sequence=0,
    amount=4000.0,
    recipients=("Tank 1",),
    event_type="direct_heal",
):
    return CombatSimulationEvent(
        time_seconds=time_seconds,
        priority=int(SimulationEventPriority.DIRECT_RESULT),
        sequence=sequence,
        event_type=event_type,
        source="Combat Prayer",
        payload=(
            ("coefficient_number", 1),
            ("modeled_heal", amount),
            ("recipients", recipients),
        ),
    )


def _state(current=20000, maximum=25000):
    return CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Tank 1",
                "ally",
                current_health=current,
                maximum_health=maximum,
            ),
        ),
        recipient_bindings=(),
    )


def test_bound_heal_projects_actual_health_change() -> None:
    result = CombatSimulationHealthService().project(
        events=(_heal_event(amount=4000.0),),
        target_state=_state(),
    )

    assert result.unresolved == ()
    assert len(result.events) == 1
    payload = result.events[0].payload_dict()
    assert payload["recipient"] == "Tank 1"
    assert payload["before"] == 20000
    assert payload["attempted_heal"] == 4000.0
    assert payload["applied_heal"] == 4000.0
    assert payload["overheal"] == 0.0
    assert payload["after"] == 24000
    assert payload["maximum_health"] == 25000


def test_overheal_is_auditable_and_health_caps_at_maximum() -> None:
    result = CombatSimulationHealthService().project(
        events=(_heal_event(amount=4000.0),),
        target_state=_state(current=23000, maximum=25000),
    )

    payload = result.events[0].payload_dict()
    assert payload["before"] == 23000
    assert payload["applied_heal"] == 2000.0
    assert payload["overheal"] == 2000.0
    assert payload["after"] == 25000


def test_sequential_bound_heals_use_prior_health_change() -> None:
    result = CombatSimulationHealthService().project(
        events=(
            _heal_event(time_seconds=1.0, sequence=0, amount=3000.0),
            _heal_event(
                time_seconds=2.0,
                sequence=0,
                amount=3000.0,
                event_type="periodic_heal",
            ),
        ),
        target_state=_state(current=19000, maximum=25000),
    )

    assert [event.payload_dict()["before"] for event in result.events] == [19000, 22000]
    assert [event.payload_dict()["after"] for event in result.events] == [22000, 25000]


def test_missing_health_state_fails_closed_without_inventing_effective_healing() -> None:
    state = CombatSimulationTargetState(
        combatants=(CombatSimulationCombatant("Tank 1", "ally"),),
        recipient_bindings=(),
    )

    result = CombatSimulationHealthService().project(
        events=(_heal_event(),),
        target_state=state,
    )

    assert result.events == ()
    assert result.unresolved == (
        "Combat Prayer direct_heal at 1s -> Tank 1: current and maximum Health are required",
    )
