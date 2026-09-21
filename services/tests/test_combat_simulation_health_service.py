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



def _damage_event(*, time_seconds=0.5, sequence=0, amount=6000.0, recipient="Tank 1"):
    return CombatSimulationEvent(
        time_seconds=time_seconds,
        priority=int(SimulationEventPriority.DIRECT_RESULT),
        sequence=sequence,
        event_type="incoming_damage",
        source="Boss Cleave",
        payload=(
            ("recipient", recipient),
            ("amount", amount),
            ("damage_type", "physical"),
        ),
    )


def test_explicit_incoming_damage_reduces_health() -> None:
    result = CombatSimulationHealthService().project(
        events=(_damage_event(amount=6000.0),),
        target_state=_state(current=20000, maximum=25000),
    )

    assert result.unresolved == ()
    payload = result.events[0].payload_dict()
    assert payload["before"] == 20000
    assert payload["attempted_damage"] == 6000.0
    assert payload["applied_damage"] == 6000.0
    assert payload["overkill"] == 0.0
    assert payload["after"] == 14000


def test_incoming_damage_caps_at_zero_and_records_overkill() -> None:
    result = CombatSimulationHealthService().project(
        events=(_damage_event(amount=12000.0),),
        target_state=_state(current=5000, maximum=25000),
    )

    payload = result.events[0].payload_dict()
    assert payload["applied_damage"] == 5000.0
    assert payload["overkill"] == 7000.0
    assert payload["after"] == 0


def test_damage_then_heal_uses_updated_health_state() -> None:
    result = CombatSimulationHealthService().project(
        events=(
            _damage_event(time_seconds=0.5, amount=6000.0),
            _heal_event(time_seconds=1.0, amount=4000.0),
        ),
        target_state=_state(current=20000, maximum=25000),
    )

    assert [event.payload_dict()["before"] for event in result.events] == [20000, 14000]
    assert [event.payload_dict()["after"] for event in result.events] == [14000, 18000]


def test_incoming_damage_missing_health_state_fails_closed() -> None:
    state = CombatSimulationTargetState(
        combatants=(CombatSimulationCombatant("Tank 1", "ally"),),
        recipient_bindings=(),
    )

    result = CombatSimulationHealthService().project(
        events=(_damage_event(),),
        target_state=state,
    )

    assert result.events == ()
    assert result.unresolved == (
        "Boss Cleave incoming_damage at 0.5s -> Tank 1: current and maximum Health are required",
    )



def test_lethal_damage_emits_explicit_death_transition() -> None:
    result = CombatSimulationHealthService().project(
        events=(_damage_event(amount=25000.0),),
        target_state=_state(current=5000, maximum=25000),
    )

    assert [event.event_type for event in result.events] == [
        "health_change",
        "death",
    ]
    death = result.events[1].payload_dict()
    assert death["recipient"] == "Tank 1"
    assert death["origin_event_type"] == "incoming_damage"


def test_nonlethal_damage_does_not_emit_death() -> None:
    result = CombatSimulationHealthService().project(
        events=(_damage_event(amount=4000.0),),
        target_state=_state(current=5000, maximum=25000),
    )

    assert [event.event_type for event in result.events] == ["health_change"]


def test_healing_dead_recipient_does_not_imply_resurrection() -> None:
    result = CombatSimulationHealthService().project(
        events=(
            _damage_event(time_seconds=0.5, amount=25000.0),
            _heal_event(time_seconds=1.0, amount=8000.0),
        ),
        target_state=_state(current=5000, maximum=25000),
    )

    assert [event.event_type for event in result.events] == [
        "health_change",
        "death",
    ]
    assert any(
        "recipient is dead; resurrection semantics are not modeled" in message
        for message in result.unresolved
    )



def _outgoing_damage_event(
    *,
    time_seconds=0.5,
    sequence=0,
    amount=6000.0,
    recipient="Boss",
):
    return CombatSimulationEvent(
        time_seconds=time_seconds,
        priority=int(SimulationEventPriority.DIRECT_RESULT),
        sequence=sequence,
        event_type="outgoing_damage",
        source="Force Pulse",
        payload=(
            ("recipient", recipient),
            ("amount", amount),
            ("damage_type", "magic"),
        ),
    )


def test_explicit_outgoing_damage_reduces_enemy_health() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=50000,
                maximum_health=50000,
            ),
        ),
    )

    result = CombatSimulationHealthService().project(
        events=(_outgoing_damage_event(amount=12000.0),),
        target_state=state,
    )

    assert result.unresolved == ()
    assert [event.event_type for event in result.events] == ["health_change"]
    payload = result.events[0].payload_dict()
    assert payload["recipient"] == "Boss"
    assert payload["before"] == 50000
    assert payload["attempted_damage"] == 12000.0
    assert payload["applied_damage"] == 12000.0
    assert payload["after"] == 38000
    assert payload["origin_event_type"] == "outgoing_damage"


def test_lethal_outgoing_damage_emits_enemy_death_transition() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=5000,
                maximum_health=50000,
            ),
        ),
    )

    result = CombatSimulationHealthService().project(
        events=(_outgoing_damage_event(amount=9000.0),),
        target_state=state,
    )

    assert [event.event_type for event in result.events] == [
        "health_change",
        "death",
    ]
    health = result.events[0].payload_dict()
    death = result.events[1].payload_dict()
    assert health["after"] == 0
    assert health["overkill"] == 4000.0
    assert death["recipient"] == "Boss"
    assert death["origin_event_type"] == "outgoing_damage"



def test_same_instant_damage_and_heal_fail_closed_for_recipient() -> None:
    result = CombatSimulationHealthService().project(
        events=(
            _damage_event(time_seconds=1.0, sequence=0, amount=6000.0),
            _heal_event(time_seconds=1.0, sequence=0, amount=4000.0),
        ),
        target_state=_state(current=20000, maximum=25000),
    )

    assert result.events == ()
    assert any(
        "Health consequence ordering is unresolved" in message
        and "Tank 1" in message
        for message in result.unresolved
    )


def test_earlier_health_history_is_preserved_before_ambiguous_boundary() -> None:
    result = CombatSimulationHealthService().project(
        events=(
            _damage_event(time_seconds=0.5, sequence=0, amount=2000.0),
            _damage_event(time_seconds=1.0, sequence=0, amount=6000.0),
            _heal_event(time_seconds=1.0, sequence=0, amount=4000.0),
            _heal_event(time_seconds=2.0, sequence=0, amount=1000.0),
        ),
        target_state=_state(current=20000, maximum=25000),
    )

    assert len(result.events) == 1
    payload = result.events[0].payload_dict()
    assert payload["before"] == 20000
    assert payload["after"] == 18000
    assert any(
        "1s #0 -> Tank 1" in message
        for message in result.unresolved
    )


def test_same_timestamp_different_sequence_remains_deterministic() -> None:
    result = CombatSimulationHealthService().project(
        events=(
            _damage_event(time_seconds=1.0, sequence=0, amount=6000.0),
            _heal_event(time_seconds=1.0, sequence=1, amount=4000.0),
        ),
        target_state=_state(current=20000, maximum=25000),
    )

    assert result.unresolved == ()
    assert [event.payload_dict()["before"] for event in result.events] == [20000, 14000]
    assert [event.payload_dict()["after"] for event in result.events] == [14000, 18000]


def test_two_same_instant_damage_sources_fail_closed() -> None:
    other = CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.DIRECT_RESULT),
        sequence=0,
        event_type="incoming_damage",
        source="Second Hit",
        payload=(
            ("recipient", "Tank 1"),
            ("amount", 3000.0),
        ),
    )
    result = CombatSimulationHealthService().project(
        events=(
            _damage_event(time_seconds=1.0, sequence=0, amount=6000.0),
            other,
        ),
        target_state=_state(current=20000, maximum=25000),
    )

    assert result.events == ()
    assert any(
        "Boss Cleave" in message and "Second Hit" in message
        for message in result.unresolved
    )



def test_health_change_priority_follows_causal_damage_event() -> None:
    result = CombatSimulationHealthService().project(
        events=(_damage_event(time_seconds=1.0, sequence=0, amount=3000.0),),
        target_state=_state(current=20000, maximum=25000),
    )

    assert [event.priority for event in result.events] == [
        int(SimulationEventPriority.HEALTH_CHANGE),
    ]
    assert int(SimulationEventPriority.DIRECT_RESULT) < int(
        SimulationEventPriority.HEALTH_CHANGE
    )


def test_earliest_health_collision_remains_blocking_boundary() -> None:
    second_damage = CombatSimulationEvent(
        time_seconds=2.0,
        priority=int(SimulationEventPriority.DIRECT_RESULT),
        sequence=0,
        event_type="incoming_damage",
        source="Second Boss Hit",
        payload=(("recipient", "Tank 1"), ("amount", 1000.0)),
    )
    second_heal = _heal_event(
        time_seconds=2.0,
        sequence=0,
        amount=500.0,
    )
    result = CombatSimulationHealthService().project(
        events=(
            _damage_event(time_seconds=1.0, sequence=0, amount=6000.0),
            _heal_event(time_seconds=1.0, sequence=0, amount=4000.0),
            second_damage,
            second_heal,
        ),
        target_state=_state(current=20000, maximum=25000),
    )

    assert result.events == ()
    assert any("1s #0 -> Tank 1" in message for message in result.unresolved)
    assert any("2s #0 -> Tank 1" in message for message in result.unresolved)


def test_health_collision_blocks_only_affected_recipient() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Tank 1",
                "ally",
                current_health=20000,
                maximum_health=25000,
            ),
            CombatSimulationCombatant(
                "Tank 2",
                "ally",
                current_health=18000,
                maximum_health=25000,
            ),
        ),
    )
    tank2_damage = CombatSimulationEvent(
        time_seconds=1.5,
        priority=int(SimulationEventPriority.DIRECT_RESULT),
        sequence=0,
        event_type="incoming_damage",
        source="Tank 2 Hit",
        payload=(("recipient", "Tank 2"), ("amount", 3000.0)),
    )

    result = CombatSimulationHealthService().project(
        events=(
            _damage_event(time_seconds=1.0, sequence=0, amount=6000.0),
            _heal_event(time_seconds=1.0, sequence=0, amount=4000.0),
            tank2_damage,
        ),
        target_state=state,
    )

    assert len(result.events) == 1
    payload = result.events[0].payload_dict()
    assert payload["recipient"] == "Tank 2"
    assert payload["before"] == 18000
    assert payload["after"] == 15000
    assert any("Tank 1" in message for message in result.unresolved)



def test_damage_after_death_does_not_emit_zero_to_zero_health_change() -> None:
    result = CombatSimulationHealthService().project(
        events=(
            _damage_event(time_seconds=1.0, sequence=0, amount=25000.0),
            _damage_event(time_seconds=2.0, sequence=0, amount=5000.0),
        ),
        target_state=_state(current=5000, maximum=25000),
    )

    assert [event.event_type for event in result.events] == [
        "health_change",
        "death",
    ]
    assert any(
        "recipient is dead; additional damage is not applied" in message
        for message in result.unresolved
    )
    assert not any(
        event.event_type == "health_change"
        and event.time_seconds == 2.0
        for event in result.events
    )
