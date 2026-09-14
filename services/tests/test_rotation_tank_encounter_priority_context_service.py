from services.raid_tank_encounter_responsibility_binding_service import (
    RaidTankEncounterBoundResponsibility,
)
from services.raid_tank_encounter_responsibility_lane_service import (
    RaidTankEncounterResponsibility,
)
from services.rotation_tank_encounter_add_taunt_handling_context_service import (
    RotationTankAddTauntHandlingContext,
)
from services.rotation_tank_encounter_priority_context_service import (
    RotationTankEncounterPriorityContextService,
)


def _bound(
    *,
    lane_id: str,
    member_id: str,
    responsibility_id: str,
    target_key: str,
    action_type: str,
    capability: str | None = None,
) -> RaidTankEncounterBoundResponsibility:
    return RaidTankEncounterBoundResponsibility(
        encounter_id="xalvakka",
        lane_id=lane_id,
        member_id=member_id,
        responsibility=RaidTankEncounterResponsibility(
            responsibility_id=responsibility_id,
            target_key=target_key,
            action_type=action_type,
            required_capability_type=capability,
            source="fixture",
        ),
    )


def test_priority_context_orders_boss_and_add_handler_work_without_hard_policy() -> None:
    boss = _bound(
        lane_id="boss_holder",
        member_id="mt",
        responsibility_id="boss_taunt",
        target_key="xalvakka",
        action_type="maintain_taunt",
        capability="taunt",
    )
    pack = _bound(
        lane_id="add_handler",
        member_id="ot",
        responsibility_id="pack_encounter_adds",
        target_key="encounter_adds",
        action_type="gather_and_stack_on_boss",
        capability="taunt",
    )
    iron_position = _bound(
        lane_id="add_handler",
        member_id="ot",
        responsibility_id="iron_atronach_opening_position",
        target_key="iron_atronach",
        action_type="place_away_then_stack",
    )
    daedroth_facing = _bound(
        lane_id="add_handler",
        member_id="ot",
        responsibility_id="daedroth_facing",
        target_key="daedroth",
        action_type="face_away_from_group",
    )
    handling = (
        RotationTankAddTauntHandlingContext(
            encounter_id="xalvakka",
            lane_id="add_handler",
            member_id="ot",
            responsibility_id="pack_encounter_adds",
            actor_name="Iron Atronach",
            handling_class="strong_taunt_maintenance_target",
            ranking_context=True,
            interpretation="fixture iron",
        ),
        RotationTankAddTauntHandlingContext(
            encounter_id="xalvakka",
            lane_id="add_handler",
            member_id="ot",
            responsibility_id="pack_encounter_adds",
            actor_name="Daedroth",
            handling_class="selective_contextual_taunt_target",
            ranking_context=True,
            interpretation="fixture daedroth",
        ),
    )

    service = RotationTankEncounterPriorityContextService()
    rows = service.for_responsibilities(
        encounter_id="xalvakka",
        responsibilities=(boss, pack, iron_position, daedroth_facing),
        handling_context=handling,
    )

    assert [(row.priority, row.directive, row.actor_name) for row in rows] == [
        (10, "maintain_primary_boss_ownership", None),
        (20, "acquire_and_maintain_owned_add_when_active", "Iron Atronach"),
        (30, "place_away_then_stack", "Iron Atronach"),
        (40, "contextual_add_pickup_when_required", "Daedroth"),
        (50, "face_away_from_group_when_owned", "Daedroth"),
    ]
    assert all(row.hard_policy is False for row in rows)


def test_priority_context_does_not_invent_actor_specific_add_policy_without_handling_context() -> None:
    pack = _bound(
        lane_id="add_handler",
        member_id="ot",
        responsibility_id="pack_encounter_adds",
        target_key="encounter_adds",
        action_type="gather_and_stack_on_boss",
        capability="taunt",
    )

    class _NoHandling:
        def for_responsibilities(self, **_kwargs):
            return ()

    service = RotationTankEncounterPriorityContextService(
        add_taunt_handling_context_service=_NoHandling()
    )
    assert service.for_responsibilities(
        encounter_id="xalvakka",
        responsibilities=(pack,),
    ) == ()
