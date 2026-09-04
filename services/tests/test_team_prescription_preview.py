from services.team_prescription import (
    PrescribedBuildChange,
    PrescribedRoster,
    PrescribedRosterAssignment,
    PrescriptionDimension,
    TeamPrescriptionScope,
)
from services.team_prescription_preview import format_prescribed_roster_preview


def test_preview_distinguishes_saved_anchor_prescribed_candidate_and_open_slot() -> None:
    scope = TeamPrescriptionScope(
        dimensions=(
            PrescriptionDimension.CLASS,
            PrescriptionDimension.BUILD,
            PrescriptionDimension.GEAR,
        )
    )
    roster = PrescribedRoster(
        name="Godslayer Prescribed Roster",
        goal="Godslayer",
        scope=scope,
        assignments=(
            PrescribedRosterAssignment(
                slot_name="Main Tank",
                player_name="Tank Player",
                source_build_name="Necro Tank",
                prescribed_role="Tank",
            ),
            PrescribedRosterAssignment(
                slot_name="DD 1",
                player_name=None,
                source_build_name="Provider DD",
                prescribed_role="DD",
                changes=(
                    PrescribedBuildChange(
                        dimension=PrescriptionDimension.CLASS,
                        current_value=None,
                        prescribed_value="Arcanist",
                        reason="structural test recommendation",
                    ),
                    PrescribedBuildChange(
                        dimension=PrescriptionDimension.BUILD,
                        current_value=None,
                        prescribed_value="Provider DD",
                        reason="structural test recommendation",
                    ),
                    PrescribedBuildChange(
                        dimension=PrescriptionDimension.GEAR,
                        current_value=None,
                        prescribed_value="Set A + Set B",
                        reason="structural test recommendation",
                    ),
                ),
            ),
            PrescribedRosterAssignment(
                slot_name="DD 2",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
                unresolved=("DD 2 still unresolved",),
            ),
        ),
        unresolved=("DD 2: candidate prescription required",),
    )

    lines = format_prescribed_roster_preview(roster)

    assert "Main Tank: Tank Player — Necro Tank" in lines
    assert "DD 1: PRESCRIBED — DD | Arcanist | Provider DD" in lines
    assert "  Gear: Set A + Set B" in lines
    assert "DD 2: TO PRESCRIBE (DD)" in lines
    assert lines[-1] == "1 unresolved roster requirement(s) remain."


def test_preview_does_not_invent_player_identity_for_prescribed_candidate() -> None:
    roster = PrescribedRoster(
        name="Trial Prescription",
        goal="Trial",
        scope=TeamPrescriptionScope(dimensions=(PrescriptionDimension.CLASS,)),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="Healer 2",
                player_name=None,
                source_build_name="Candidate Build",
                prescribed_role="Healer",
                changes=(
                    PrescribedBuildChange(
                        dimension=PrescriptionDimension.CLASS,
                        current_value=None,
                        prescribed_value="Warden",
                        reason="structural test recommendation",
                    ),
                ),
            ),
        ),
    )

    lines = format_prescribed_roster_preview(roster)

    assert "Healer 2: PRESCRIBED — Healer | Warden" in lines
    assert all("Candidate Build —" not in line for line in lines)
