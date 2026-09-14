from services.raid_plan_tank_triggered_responsibility_service import (
    RaidPlanTankTriggeredResponsibilityService,
)
from services.rotation_tank_encounter_add_activity_trigger_service import (
    RotationTankEncounterAddActivityTrigger,
)
from services.rotation_tank_encounter_priority_context_service import (
    RotationTankEncounterPriorityCue,
)


def _activity(actor_name: str, responsibility_id: str) -> RotationTankEncounterAddActivityTrigger:
    return RotationTankEncounterAddActivityTrigger(
        encounter_id="xalvakka",
        lane_id="add_handler",
        member_id="tank-b",
        responsibility_id=responsibility_id,
        action_type="maintain_taunt",
        actor_name=actor_name,
        activity_boundary="earliest_source_or_involving_event",
        required_capability_type="taunt",
        source="reviewed add activity",
    )


def _priority(
    actor_name: str,
    responsibility_id: str,
    *,
    directive: str,
    trigger: str,
    priority: int,
) -> RotationTankEncounterPriorityCue:
    return RotationTankEncounterPriorityCue(
        encounter_id="xalvakka",
        lane_id="add_handler",
        member_id="tank-b",
        priority=priority,
        responsibility_id=responsibility_id,
        target_key="encounter_adds",
        actor_name=actor_name,
        directive=directive,
        trigger=trigger,
        hard_policy=False,
        interpretation="reviewed actor-specific handling",
    )


def test_strong_reviewed_add_activity_becomes_triggered_plan_responsibility() -> None:
    result = RaidPlanTankTriggeredResponsibilityService().project(
        seat_id="off-tank",
        add_activity_triggers=(
            _activity("Iron Atronach", "pack_encounter_adds"),
        ),
        priority_context=(
            _priority(
                "Iron Atronach",
                "pack_encounter_adds",
                directive="acquire_and_maintain_owned_add_when_active",
                trigger="reviewed_add_activity",
                priority=20,
            ),
        ),
    )

    assert result.resolved is True
    assert result.unresolved == ()
    assert len(result.responsibilities) == 1
    responsibility = result.responsibilities[0]
    assert responsibility.seat_id == "off-tank"
    assert responsibility.encounter_id == "xalvakka"
    assert responsibility.trigger_key == "encounter_actor_active:iron_atronach"
    assert responsibility.directive == "acquire_and_maintain_owned_add_when_active"
    assert responsibility.target_key == "Iron Atronach"
    assert responsibility.required_capability_type == "taunt"
    assert not hasattr(responsibility, "time_seconds")


def test_contextual_add_handling_stays_unresolved_without_extra_context() -> None:
    result = RaidPlanTankTriggeredResponsibilityService().project(
        seat_id="off-tank",
        add_activity_triggers=(
            _activity("Daedroth", "pack_encounter_adds"),
        ),
        priority_context=(
            _priority(
                "Daedroth",
                "pack_encounter_adds",
                directive="contextual_add_pickup_when_required",
                trigger="reviewed_add_activity_and_encounter_context",
                priority=40,
            ),
        ),
    )

    assert result.responsibilities == ()
    assert result.resolved is False
    assert result.unresolved == (
        "Daedroth: Tank responsibility requires additional encounter context before it can become triggered plan intent",
    )


def test_activity_without_matching_priority_context_fails_closed() -> None:
    result = RaidPlanTankTriggeredResponsibilityService().project(
        seat_id="off-tank",
        add_activity_triggers=(
            _activity("Iron Atronach", "pack_encounter_adds"),
        ),
        priority_context=(),
    )

    assert result.responsibilities == ()
    assert result.unresolved == (
        "Iron Atronach: reviewed add activity has no matching Tank priority context",
    )


def test_projection_never_promotes_soft_priority_to_hard_policy() -> None:
    cue = _priority(
        "Iron Atronach",
        "pack_encounter_adds",
        directive="acquire_and_maintain_owned_add_when_active",
        trigger="reviewed_add_activity",
        priority=20,
    )

    assert cue.hard_policy is False
    result = RaidPlanTankTriggeredResponsibilityService().project(
        seat_id="off-tank",
        add_activity_triggers=(
            _activity("Iron Atronach", "pack_encounter_adds"),
        ),
        priority_context=(cue,),
    )

    assert result.responsibilities
    assert not hasattr(result.responsibilities[0], "hard_policy")
