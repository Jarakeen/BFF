from services.raid_tank_encounter_responsibility_lane_assignment_service import (
    RaidTankEncounterResponsibilityLaneAssignmentService,
)
from services.raid_tank_encounter_responsibility_lane_service import (
    RaidTankEncounterResponsibilityLaneService,
)


def _plan():
    plan = RaidTankEncounterResponsibilityLaneService().for_encounter("xalvakka")
    assert plan is not None
    return plan


def test_explicit_xalvakka_lane_assignment_accepts_distinct_taunt_capable_tanks():
    result = RaidTankEncounterResponsibilityLaneAssignmentService().resolve(
        plan=_plan(),
        lane_member_ids={
            "boss_holder": "tank-a",
            "add_handler": "tank-b",
        },
        member_capabilities={
            "tank-a": {"taunt"},
            "tank-b": {"taunt"},
        },
    )

    assert result.resolved is True
    assert [(row.lane_id, row.member_id) for row in result.assignments] == [
        ("boss_holder", "tank-a"),
        ("add_handler", "tank-b"),
    ]
    assert result.unresolved == ()


def test_same_member_cannot_fill_distinct_xalvakka_lanes():
    result = RaidTankEncounterResponsibilityLaneAssignmentService().resolve(
        plan=_plan(),
        lane_member_ids={
            "boss_holder": "tank-a",
            "add_handler": "tank-a",
        },
        member_capabilities={"tank-a": {"taunt"}},
    )

    assert result.resolved is False
    assert len(result.unresolved) == 1
    assert "distinct Tank lanes" in result.unresolved[0]
    assert "tank-a" in result.unresolved[0]


def test_lane_assignment_requires_explicit_member_for_every_reviewed_lane():
    result = RaidTankEncounterResponsibilityLaneAssignmentService().resolve(
        plan=_plan(),
        lane_member_ids={"boss_holder": "tank-a"},
        member_capabilities={"tank-a": {"taunt"}},
    )

    assert result.resolved is False
    assert any("add_handler" in row and "assignment is missing" in row for row in result.unresolved)


def test_lane_assignment_fails_closed_when_required_capability_is_not_proven():
    result = RaidTankEncounterResponsibilityLaneAssignmentService().resolve(
        plan=_plan(),
        lane_member_ids={
            "boss_holder": "tank-a",
            "add_handler": "tank-b",
        },
        member_capabilities={
            "tank-a": {"taunt"},
            "tank-b": {"interrupt"},
        },
    )

    assert result.resolved is False
    assert any(
        "add_handler" in row and "lacks required canonical capability evidence: taunt" in row
        for row in result.unresolved
    )


def test_lane_assignment_fails_closed_when_member_capability_evidence_is_missing():
    result = RaidTankEncounterResponsibilityLaneAssignmentService().resolve(
        plan=_plan(),
        lane_member_ids={
            "boss_holder": "tank-a",
            "add_handler": "tank-b",
        },
        member_capabilities={"tank-a": {"taunt"}},
    )

    assert result.resolved is False
    assert any(
        "add_handler" in row and "capability evidence is unavailable" in row
        for row in result.unresolved
    )
