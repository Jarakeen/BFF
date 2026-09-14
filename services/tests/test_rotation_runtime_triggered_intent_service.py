import pytest

from models.raid_plan import RaidPlanTriggeredResponsibility
from services.rotation_runtime_triggered_intent_service import (
    RotationRuntimeTriggeredIntentService,
)


def _responsibility(*, seat_id: str = "off-tank") -> RaidPlanTriggeredResponsibility:
    return RaidPlanTriggeredResponsibility(
        responsibility_id="xalvakka:pack_encounter_adds:iron_atronach",
        seat_id=seat_id,
        encounter_id="xalvakka",
        trigger_key="encounter_actor_active:iron_atronach",
        directive="acquire_and_maintain_owned_add_when_active",
        target_key="Iron Atronach",
        required_capability_type="taunt",
        source="reviewed Tank add activity",
    )


def test_raid_plan_responsibility_projects_to_pending_rotation_intent_without_time() -> None:
    intents = RotationRuntimeTriggeredIntentService().project(
        plan_id="performance-mode-rg",
        seat_id="off-tank",
        responsibilities=(_responsibility(),),
    )

    assert len(intents) == 1
    intent = intents[0]
    assert intent.intent_id == "xalvakka:pack_encounter_adds:iron_atronach"
    assert intent.source_plan_id == "performance-mode-rg"
    assert intent.source_seat_id == "off-tank"
    assert intent.encounter_id == "xalvakka"
    assert intent.trigger_key == "encounter_actor_active:iron_atronach"
    assert intent.directive == "acquire_and_maintain_owned_add_when_active"
    assert intent.required_capability_type == "taunt"
    assert not hasattr(intent, "time_seconds")


def test_runtime_intent_projection_rejects_cross_seat_responsibility() -> None:
    with pytest.raises(ValueError, match="does not belong"):
        RotationRuntimeTriggeredIntentService().project(
            plan_id="performance-mode-rg",
            seat_id="off-tank",
            responsibilities=(_responsibility(seat_id="main-tank"),),
        )


def test_runtime_intent_projection_requires_plan_and_seat_identity() -> None:
    service = RotationRuntimeTriggeredIntentService()
    with pytest.raises(ValueError, match="plan_id"):
        service.project(plan_id="", seat_id="off-tank", responsibilities=())
    with pytest.raises(ValueError, match="seat_id"):
        service.project(plan_id="performance-mode-rg", seat_id="", responsibilities=())
