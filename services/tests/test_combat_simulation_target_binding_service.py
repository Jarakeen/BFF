from __future__ import annotations

from models.combat_simulation import (
    CombatSimulationCombatant,
    CombatSimulationEvent,
    CombatSimulationIncomingDamage,
    CombatSimulationRecipientBinding,
    CombatSimulationResourceResult,
    CombatSimulationTargetState,
    SimulationEventPriority,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from models.effective_build_snapshot import EffectiveBuildSnapshot
from services.combat_simulation_healing_service import CombatSimulationHealingProjection
from services.combat_simulation_resource_service import CombatSimulationResourceProjection
from services.combat_simulation_service import CombatSimulationService
from services.combat_simulation_skill_effect_service import CombatSimulationEffectProjection
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



class _ResourceService:
    def project(self, **_kwargs):
        return CombatSimulationResourceProjection(
            result=CombatSimulationResourceResult(
                resource="magicka",
                starting_amount=30000,
                ending_amount=30000,
            ),
            events=(),
            unresolved=(),
        )


class _HealingService:
    def project(self, **_kwargs):
        return CombatSimulationHealingProjection(
            events=(_heal_event(),),
            unresolved=(),
        )


class _EffectService:
    def project(self, **_kwargs):
        return CombatSimulationEffectProjection(
            events=(_effect_event(),),
            windows=(),
            unresolved=(),
        )


def test_main_simulation_binds_known_recipients_without_inventing_others() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=3.0,
        actions=(
            RotationAction(
                1.0,
                0,
                RotationActionKind.SKILL,
                name="Combat Prayer",
                bar="front",
            ),
        ),
    )
    snapshot = EffectiveBuildSnapshot.from_saved_build(
        PlayerBuild(
            Name="Magrat",
            BuildName="DF Healer",
            Role="Healer",
            EsoClass="Warden",
        )
    )
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant("Magrat", "self"),
            CombatSimulationCombatant("Tank 1", "ally"),
        ),
        recipient_bindings=(
            CombatSimulationRecipientBinding(
                time_seconds=1.0,
                sequence=0,
                event_type="direct_heal",
                source="Combat Prayer",
                coefficient_number=1,
                recipients=("Tank 1",),
            ),
            CombatSimulationRecipientBinding(
                time_seconds=1.0,
                sequence=0,
                event_type="effect_apply",
                source="Combat Prayer",
                effect_name="minor_resolve",
                recipients=("Tank 1",),
            ),
        ),
    )

    result = CombatSimulationService(
        resource_service=_ResourceService(),
        healing_service=_HealingService(),
        skill_effect_service=_EffectService(),
    ).simulate(
        build_snapshot=snapshot,
        plan=plan,
        target_state=state,
    )

    heal = next(event for event in result.events if event.event_type == "direct_heal")
    effect = next(event for event in result.events if event.event_type == "effect_apply")
    assert heal.payload_dict()["recipients"] == ("Tank 1",)
    assert effect.payload_dict()["recipients"] == ("Tank 1",)
    assert result.target_state == state
    assert not any("explicit recipient binding is required" in item for item in result.unresolved)



def test_target_state_rejects_duplicate_event_binding_identity() -> None:
    binding = CombatSimulationRecipientBinding(
        time_seconds=1.0,
        sequence=0,
        event_type="direct_heal",
        source="Combat Prayer",
        coefficient_number=1,
        recipients=("Tank 1",),
    )

    try:
        CombatSimulationTargetState(
            combatants=(CombatSimulationCombatant("Tank 1", "ally"),),
            recipient_bindings=(binding, binding),
        )
    except ValueError as exc:
        assert "recipient binding identities must be unique" in str(exc)
    else:
        raise AssertionError("Expected duplicate recipient binding identity to fail closed")



def test_main_simulation_merges_explicit_incoming_damage_and_health_change() -> None:
    plan = RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=3.0,
        actions=(),
    )
    snapshot = EffectiveBuildSnapshot.from_saved_build(
        PlayerBuild(
            Name="Magrat",
            BuildName="DF Healer",
            Role="Healer",
            EsoClass="Warden",
        )
    )
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

    result = CombatSimulationService(
        resource_service=_ResourceService(),
        healing_service=_HealingService(),
        skill_effect_service=_EffectService(),
    ).simulate(
        build_snapshot=snapshot,
        plan=plan,
        target_state=state,
        incoming_damage=(
            CombatSimulationIncomingDamage(
                time_seconds=0.5,
                sequence=0,
                source="Boss Cleave",
                recipient="Tank 1",
                amount=6000.0,
                damage_type="physical",
            ),
        ),
    )

    incoming = next(event for event in result.events if event.event_type == "incoming_damage")
    change = next(
        event
        for event in result.events
        if event.event_type == "health_change"
        and event.source == "Boss Cleave"
    )
    assert incoming.payload_dict()["recipient"] == "Tank 1"
    assert incoming.payload_dict()["amount"] == 6000.0
    assert change.payload_dict()["before"] == 20000
    assert change.payload_dict()["after"] == 14000


def test_recipient_binding_normalizes_matching_identity_fields() -> None:
    state = CombatSimulationTargetState(
        combatants=(CombatSimulationCombatant("Tank 1", "ally"),),
        recipient_bindings=(
            CombatSimulationRecipientBinding(
                time_seconds=1.0,
                sequence=0,
                event_type=" direct_heal ",
                source=" Combat Prayer ",
                coefficient_number=1,
                recipients=(" Tank 1 ",),
            ),
        ),
    )

    result = CombatSimulationTargetBindingService().bind(
        events=(_heal_event(),),
        target_state=state,
    )

    assert result.unresolved == ()
    assert result.events[0].payload_dict()["recipients"] == ("Tank 1",)
