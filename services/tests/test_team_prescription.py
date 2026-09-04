import pytest

from services.team_prescription import (
    PrescribedBuildChange,
    PrescribedRoster,
    PrescribedRosterAssignment,
    PrescriptionDimension,
    TeamPrescriptionScope,
)


def test_prescribed_roster_allows_explicit_class_race_and_gear_changes() -> None:
    scope = TeamPrescriptionScope(
        dimensions=(
            PrescriptionDimension.CLASS,
            PrescriptionDimension.RACE,
            PrescriptionDimension.GEAR,
        )
    )
    assignment = PrescribedRosterAssignment(
        slot_name="Healer 1",
        player_name="Keen",
        source_build_name="DF Healer",
        prescribed_role="Healer",
        changes=(
            PrescribedBuildChange(
                dimension=PrescriptionDimension.CLASS,
                current_value="Templar",
                prescribed_value="Warden",
                reason="test prescription requires the selected support class",
            ),
            PrescribedBuildChange(
                dimension=PrescriptionDimension.RACE,
                current_value="Breton",
                prescribed_value="High Elf",
                reason="test prescription changes the offensive stat profile",
            ),
            PrescribedBuildChange(
                dimension=PrescriptionDimension.GEAR,
                current_value="Current saved gear",
                prescribed_value="SPC + Pillager",
                reason="test prescription requires this support-set pairing",
            ),
        ),
    )

    roster = PrescribedRoster(
        name="Fun Trial Prescription",
        goal="Godslayer",
        scope=scope,
        assignments=(assignment,),
    )

    assert roster.assignments[0].player_name == "Keen"
    assert roster.assignments[0].prescribed_role == "Healer"
    assert roster.assignments[0].change_for(PrescriptionDimension.CLASS).prescribed_value == "Warden"
    assert roster.assignments[0].change_for(PrescriptionDimension.GEAR).prescribed_value == "SPC + Pillager"


def test_prescribed_roster_rejects_change_outside_allowed_scope() -> None:
    assignment = PrescribedRosterAssignment(
        slot_name="DD 1",
        player_name="Player A",
        source_build_name="Current DD",
        prescribed_role="DD",
        changes=(
            PrescribedBuildChange(
                dimension=PrescriptionDimension.RACE,
                current_value="Khajiit",
                prescribed_value="Dark Elf",
                reason="test optimizer alternative",
            ),
        ),
    )

    with pytest.raises(ValueError, match="exceeds optimization scope"):
        PrescribedRoster(
            name="Locked Race Team",
            goal="Planebreaker",
            scope=TeamPrescriptionScope(dimensions=(PrescriptionDimension.GEAR,)),
            assignments=(assignment,),
        )


def test_prescribed_roster_rejects_same_player_in_multiple_slots() -> None:
    assignment_a = PrescribedRosterAssignment(
        slot_name="Healer 1",
        player_name="Player A",
        source_build_name="Heal",
        prescribed_role="Healer",
    )
    assignment_b = PrescribedRosterAssignment(
        slot_name="DD 1",
        player_name="Player A",
        source_build_name="DD",
        prescribed_role="DD",
    )

    with pytest.raises(ValueError, match="multiple roster slots"):
        PrescribedRoster(
            name="Impossible Team",
            goal="Custom Goal",
            scope=TeamPrescriptionScope(),
            assignments=(assignment_a, assignment_b),
        )


def test_prescription_is_not_a_saved_build_mutation() -> None:
    change = PrescribedBuildChange(
        dimension=PrescriptionDimension.CLASS,
        current_value="Nightblade",
        prescribed_value="Arcanist",
        reason="structural recommendation only",
    )
    assignment = PrescribedRosterAssignment(
        slot_name="DD 1",
        player_name="Player A",
        source_build_name="Existing Build",
        prescribed_role="DD",
        changes=(change,),
    )

    assert assignment.source_build_name == "Existing Build"
    assert assignment.change_for(PrescriptionDimension.CLASS).current_value == "Nightblade"
    assert assignment.change_for(PrescriptionDimension.CLASS).prescribed_value == "Arcanist"
