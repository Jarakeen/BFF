from types import SimpleNamespace

import pytest

from services.raid_tank_encounter_responsibility_binding_service import (
    RaidTankEncounterBoundResponsibility,
)
from services.raid_tank_encounter_responsibility_lane_service import (
    RaidTankEncounterResponsibility,
)
from services.rotation_tank_encounter_add_activity_trigger_service import (
    RotationTankEncounterAddActivityTriggerService,
)


class _ActivityService:
    def __init__(self, plan):
        self.plan = plan
        self.calls = []

    def reviewed_for(self, encounter_id):
        self.calls.append(encounter_id)
        return self.plan


def _actor(name, *, fully=True):
    observed = 3
    coverage = observed if fully else observed - 1
    return SimpleNamespace(
        actor_name=name,
        activity_boundary="earliest_source_or_involving_event",
        observed_instances=observed,
        involving_coverage=coverage,
        source_coverage=coverage,
        cast_coverage=coverage,
        interpretation=f"reviewed observed boundary for {name}",
        fully_observed_source_boundary=fully,
    )


def _bound(responsibility_id, target_key, action_type, capability=None):
    return RaidTankEncounterBoundResponsibility(
        encounter_id="xalvakka",
        lane_id="add_handler",
        member_id="tank-b",
        responsibility=RaidTankEncounterResponsibility(
            responsibility_id=responsibility_id,
            target_key=target_key,
            action_type=action_type,
            required_capability_type=capability,
            source="reviewed responsibility",
        ),
    )


def test_encounter_adds_responsibility_projects_all_fully_observed_reviewed_adds():
    activity = _ActivityService(
        SimpleNamespace(
            actors=(
                _actor("Iron Atronach"),
                _actor("Daedroth"),
            )
        )
    )
    service = RotationTankEncounterAddActivityTriggerService(activity)

    result = service.for_responsibilities(
        encounter_id="xalvakka",
        responsibilities=(
            _bound(
                "pack_encounter_adds",
                "encounter_adds",
                "gather_and_stack_on_boss",
                "taunt",
            ),
        ),
    )

    assert [row.actor_name for row in result] == ["Iron Atronach", "Daedroth"]
    assert all(row.member_id == "tank-b" for row in result)
    assert all(row.activity_boundary == "earliest_source_or_involving_event" for row in result)
    assert all(row.required_capability_type == "taunt" for row in result)


def test_specific_add_responsibilities_project_only_matching_actor():
    activity = _ActivityService(
        SimpleNamespace(actors=(_actor("Iron Atronach"), _actor("Daedroth")))
    )
    service = RotationTankEncounterAddActivityTriggerService(activity)

    result = service.for_responsibilities(
        encounter_id="xalvakka",
        responsibilities=(
            _bound(
                "iron_atronach_opening_position",
                "iron_atronach",
                "place_away_then_stack",
            ),
            _bound("daedroth_facing", "daedroth", "face_away_from_group"),
        ),
    )

    assert [(row.responsibility_id, row.actor_name) for row in result] == [
        ("iron_atronach_opening_position", "Iron Atronach"),
        ("daedroth_facing", "Daedroth"),
    ]


def test_incomplete_reviewed_boundary_is_not_promoted_to_trigger():
    activity = _ActivityService(
        SimpleNamespace(actors=(_actor("Iron Atronach", fully=False),))
    )
    service = RotationTankEncounterAddActivityTriggerService(activity)

    result = service.for_responsibilities(
        encounter_id="xalvakka",
        responsibilities=(
            _bound(
                "pack_encounter_adds",
                "encounter_adds",
                "gather_and_stack_on_boss",
                "taunt",
            ),
        ),
    )

    assert result == ()


def test_mismatched_encounter_fails_closed():
    activity = _ActivityService(SimpleNamespace(actors=(_actor("Iron Atronach"),)))
    service = RotationTankEncounterAddActivityTriggerService(activity)
    row = _bound("pack_encounter_adds", "encounter_adds", "gather_and_stack_on_boss", "taunt")

    with pytest.raises(ValueError, match="encounter does not match"):
        service.for_responsibilities(
            encounter_id="taleria_hm",
            responsibilities=(row,),
        )
