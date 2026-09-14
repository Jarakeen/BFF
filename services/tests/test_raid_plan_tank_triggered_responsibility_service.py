from models.raid_plan import RaidPlan, RaidPlanMember, RaidPlanTriggeredResponsibility
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


def _plan(*, triggered=()) -> RaidPlan:
    return RaidPlan(
        plan_id="performance-mode-rockgrove",
        trial_id="rockgrove",
        name="Performance Mode - Rockgrove",
        members=(
            RaidPlanMember(
                seat_id="off-tank",
                gamertag="TankTwo",
                role="Tank",
            ),
        ),
        triggered_responsibilities=tuple(triggered),
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


def test_apply_to_plan_adds_resolved_intent_without_mutating_original_plan() -> None:
    original = _plan()
    result = RaidPlanTankTriggeredResponsibilityService().apply_to_plan(
        plan=original,
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

    assert original.triggered_responsibilities == ()
    assert result.resolved is True
    assert len(result.applied) == 1
    assert result.plan.triggered_for_seat("off-tank", encounter_id="xalvakka") == result.applied


def test_apply_to_plan_is_idempotent_for_identical_existing_intent() -> None:
    service = RaidPlanTankTriggeredResponsibilityService()
    projection = service.project(
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
    existing = projection.responsibilities[0]

    result = service.apply_to_plan(
        plan=_plan(triggered=(existing,)),
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
    assert result.plan.triggered_responsibilities == (existing,)
    assert result.applied == (existing,)


def test_apply_to_plan_preserves_conflicting_existing_raid_lead_intent() -> None:
    existing = RaidPlanTriggeredResponsibility(
        responsibility_id="xalvakka:pack_encounter_adds:iron_atronach",
        seat_id="off-tank",
        encounter_id="xalvakka",
        trigger_key="encounter_actor_active:iron_atronach",
        directive="raid_lead_custom_iron_atronach_plan",
        target_key="Iron Atronach",
        required_capability_type="taunt",
        source="explicit raid lead plan",
    )

    result = RaidPlanTankTriggeredResponsibilityService().apply_to_plan(
        plan=_plan(triggered=(existing,)),
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

    assert result.resolved is False
    assert result.applied == ()
    assert result.plan.triggered_responsibilities == (existing,)
    assert result.unresolved == (
        "xalvakka:pack_encounter_adds:iron_atronach: Raid Plan already contains different triggered responsibility intent; existing plan decision preserved",
    )


def test_apply_to_plan_rejects_unknown_seat() -> None:
    service = RaidPlanTankTriggeredResponsibilityService()

    try:
        service.apply_to_plan(
            plan=_plan(),
            seat_id="main-tank",
            add_activity_triggers=(),
            priority_context=(),
        )
    except ValueError as exc:
        assert "unknown Raid Plan seat" in str(exc)
    else:
        raise AssertionError("expected unknown Raid Plan seat to fail closed")
