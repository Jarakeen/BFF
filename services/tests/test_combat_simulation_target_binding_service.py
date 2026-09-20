from __future__ import annotations

from models.combat_simulation import (
    CombatSimulationCombatant,
    CombatSimulationEvent,
    CombatSimulationRecipientBinding,
    CombatSimulationTargetState,
    SimulationEventPriority,
)
from services.combat_simulation_target_binding_service import (
    CombatSimulationTargetBindingService,
)


def _heal_event() -> CombatSimulationEvent:
    return CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.DIRECT_RESULT),
        sequence=0,
        event_type="direct_heal",
        source="Combat Prayer",
        payload=(
            ("coefficient_number", 1),
            ("modeled_heal", 8123.5),
        ),
    )


def _effect_event() -> CombatSimulationEvent:
    return CombatSimulationEvent(
        time_seconds=1.0,
        priority=int(SimulationEventPriority.EFFECT_APPLY),
        sequence=0,
        event_type="effect_apply",
        source="Combat Prayer",
        payload=(
            ("effect_name", "minor_resolve"),
            ("target_scope", "group"),
            ("magnitude", 2974.0),
            ("duration_seconds", 10.0),
            ("category", "buff"),
            ("stacking", "unique"),
        ),
    )


def test_explicit_ally_recipients_bind_to_heal_and_group_effect() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant("Magrat", "self"),
            CombatSimulationCombatant("Tank 1", "ally"),
            CombatSimulationCombatant("DD 1", "ally"),
        ),
        recipient_bindings=(
            CombatSimulationRecipientBinding(
                time_seconds=1.0,
                sequence=0,
                event_type="direct_heal",
                source="Combat Prayer",
                coefficient_number=1,
                recipients=("Tank 1", "DD 1"),
            ),
            CombatSimulationRecipientBinding(
                time_seconds=1.0,
                sequence=0,
                event_type="effect_apply",
                source="Combat Prayer",
                effect_name="minor_resolve",
                recipients=("Tank 1", "DD 1"),
            ),
        ),
    )

    result = CombatSimulationTargetBindingService().bind(
        events=(_heal_event(), _effect_event()),
        target_state=state,
    )

    assert result.unresolved == ()
    assert result.events[0].payload_dict()["recipients"] == ("Tank 1", "DD 1")
    assert result.events[1].payload_dict()["recipients"] == ("Tank 1", "DD 1")


def test_missing_target_state_keeps_events_and_surfaces_recipient_boundary() -> None:
    events = (_heal_event(), _effect_event())
    result = CombatSimulationTargetBindingService().bind(
        events=events,
        target_state=None,
    )

    assert result.events == events
    assert len(result.unresolved) == 2
    assert all("explicit recipient binding is required" in item for item in result.unresolved)


def test_enemy_cannot_be_bound_to_heal_or_group_buff() -> None:
    state = CombatSimulationTargetState(
        combatants=(CombatSimulationCombatant("Boss", "enemy"),),
        recipient_bindings=(
            CombatSimulationRecipientBinding(
                time_seconds=1.0,
                sequence=0,
                event_type="direct_heal",
                source="Combat Prayer",
                coefficient_number=1,
                recipients=("Boss",),
            ),
        ),
    )

    result = CombatSimulationTargetBindingService().bind(
        events=(_heal_event(),),
        target_state=state,
    )

    assert "conflicts with target scope" in result.unresolved[0]
    assert "recipients" not in result.events[0].payload_dict()


def test_unknown_bound_recipient_fails_closed() -> None:
    state = CombatSimulationTargetState(
        combatants=(CombatSimulationCombatant("Magrat", "self"),),
        recipient_bindings=(
            CombatSimulationRecipientBinding(
                time_seconds=1.0,
                sequence=0,
                event_type="direct_heal",
                source="Combat Prayer",
                coefficient_number=1,
                recipients=("Mystery DD",),
            ),
        ),
    )

    result = CombatSimulationTargetBindingService().bind(
        events=(_heal_event(),),
        target_state=state,
    )

    assert result.unresolved == (
        "Combat Prayer direct_heal at 1s: recipient binding references unknown combatant(s): Mystery DD",
    )
