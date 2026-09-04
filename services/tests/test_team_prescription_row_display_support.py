import json

from models.build_model import PlayerBuild
from services.team_prescription import (
    PrescribedBuildChange,
    PrescribedRosterAssignment,
    PrescriptionDimension,
)
from ui.team_prescription_row_display_support import prescribed_recruit_row_values


def _change(dimension: PrescriptionDimension, value: str) -> PrescribedBuildChange:
    return PrescribedBuildChange(
        dimension=dimension,
        current_value=None,
        prescribed_value=value,
        reason="template evidence",
    )


def test_ingredient_only_open_chair_keeps_generic_recruit_row() -> None:
    assignment = PrescribedRosterAssignment(
        slot_name="Healer 1",
        player_name=None,
        source_build_name=None,
        prescribed_role="Healer",
        changes=(
            _change(PrescriptionDimension.CLASS, "Warden"),
            _change(PrescriptionDimension.GEAR, "Serpent's Disdain"),
        ),
    )

    assert assignment.is_open_for_candidate
    assert prescribed_recruit_row_values(assignment) is None


def test_partial_template_row_shows_known_recruit_requirements() -> None:
    assignment = PrescribedRosterAssignment(
        slot_name="Healer 1",
        player_name=None,
        source_build_name="Warden Healer — Taleria",
        prescribed_role="Healer",
        changes=(
            _change(PrescriptionDimension.CLASS, "Warden"),
            _change(
                PrescriptionDimension.GEAR,
                "Serpent's Disdain + Pillager's Profit",
            ),
            _change(
                PrescriptionDimension.SKILLS,
                "Combat Prayer / Energy Orb",
            ),
            _change(PrescriptionDimension.MUNDUS, "The Ritual"),
        ),
        unresolved=("traits", "champion_points"),
    )

    values = prescribed_recruit_row_values(assignment)

    assert values is not None
    eso_class, build_name, responsibilities, status = values
    assert eso_class == "Warden"
    assert build_name == "Warden Healer — Taleria"
    assert "Serpent's Disdain + Pillager's Profit" in responsibilities
    assert "Combat Prayer / Energy Orb" in responsibilities
    assert "The Ritual" in responsibilities
    assert "2 unresolved field(s)" in responsibilities
    assert status == "TEMPLATE"


def test_complete_template_row_shows_saveable_prescribed_build_requirements() -> None:
    build = PlayerBuild(
        BuildName="Published Warden Healer",
        EsoClass="Warden",
        Role="Healer",
    )
    build.Armor["Head"]["Set"] = "Pillager's Profit"
    build.Armor["Chest"]["Set"] = "Spell Power Cure"
    assignment = PrescribedRosterAssignment(
        slot_name="Healer 1",
        player_name=None,
        source_build_name="Published Warden Healer",
        prescribed_role="Healer",
        prescribed_build_json=json.dumps(build.to_dict()),
    )

    values = prescribed_recruit_row_values(assignment)

    assert values is not None
    eso_class, build_name, responsibilities, status = values
    assert eso_class == "Warden"
    assert build_name == "Published Warden Healer"
    assert "Pillager's Profit" in responsibilities
    assert "Spell Power Cure" in responsibilities
    assert status == "PRESCRIBED"


def test_saved_player_row_is_not_redecorated_as_recruit() -> None:
    assignment = PrescribedRosterAssignment(
        slot_name="Healer 1",
        player_name="Keen",
        source_build_name="DF Healer",
        prescribed_role="Healer",
    )

    assert prescribed_recruit_row_values(assignment) is None
