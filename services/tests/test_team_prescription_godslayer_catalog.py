from pathlib import Path

from services.team_prescription import (
    PrescriptionDimension,
    TeamPrescriptionScope,
)
from services.team_prescription_generator import generate_prescribed_roster_from_saved_builds
from services.team_prescription_template_sources import apply_team_template_sources


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"


def _change_value(assignment, dimension: PrescriptionDimension) -> str:
    change = assignment.change_for(dimension)
    return "" if change is None else str(change.prescribed_value or "").strip()


def test_u50_godslayer_catalog_prescribes_concrete_open_chair_classes() -> None:
    slots = (
        "Main Tank",
        "Off Tank",
        "Healer 1",
        "Healer 2",
        "DD 1",
        "DD 2",
        "DD 3",
        "DD 4",
        "DD 5",
        "DD 6",
        "DD 7",
        "DD 8",
    )
    roster = generate_prescribed_roster_from_saved_builds(
        name="Godslayer Prescribed Roster",
        goal="Godslayer",
        slot_labels=slots,
        builds=(),
        scope=TeamPrescriptionScope(
            dimensions=(
                PrescriptionDimension.CLASS,
                PrescriptionDimension.BUILD,
                PrescriptionDimension.GEAR,
            )
        ),
    )

    result = apply_team_template_sources(
        roster=roster,
        goal="Godslayer",
        data_dir=DATA_DIR,
    )

    assert result.published_template_count == 9
    assert result.applied_count == 12

    classes = {
        assignment.slot_name: _change_value(
            assignment,
            PrescriptionDimension.CLASS,
        )
        for assignment in result.final_roster.assignments
    }
    assert classes == {
        "Main Tank": "Dragonknight",
        "Off Tank": "Sorcerer",
        "Healer 1": "Warden",
        "Healer 2": "Arcanist",
        "DD 1": "Dragonknight",
        "DD 2": "Dragonknight",
        "DD 3": "Necromancer",
        "DD 4": "Necromancer",
        "DD 5": "Sorcerer",
        "DD 6": "Sorcerer",
        "DD 7": "Nightblade",
        "DD 8": "Templar",
    }

    assert all(
        assignment.has_candidate_recommendation
        for assignment in result.final_roster.assignments
    )
    assert not any(
        assignment.is_open_for_candidate
        for assignment in result.final_roster.assignments
    )
