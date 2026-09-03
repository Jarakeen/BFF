import pytest

from minmax.recruitment import RecruitmentPlanner, RecruitmentRequirement
from minmax.roster_types import Role


def test_hybrid_plan_fills_remaining_slots_with_recruitment_requirements():
    planner = RecruitmentPlanner(dd_minimum_parse_damage=165_000)

    result = planner.build_plan(
        party_size=12,
        real_member_count=2,
        open_role_labels=(
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
        ),
    )

    assert result.real_member_count == 2
    assert result.open_slot_count == 10
    assert result.complete_slot_count == 12
    assert result.requirements[0].role is Role.HEALER
    assert result.requirements[2].role is Role.DD
    assert result.requirements[2].minimum_parse_damage == 165_000
    assert result.requirements[2].hypothetical is True


def test_requirement_summary_distinguishes_dd_parse_from_support_experience():
    planner = RecruitmentPlanner()

    dd = planner.create_requirement(slot_id="dd-1", role_label="DD 1")
    healer = planner.create_requirement(slot_id="healer-1", role_label="Healer 1")

    assert dd.qualification_summary == "165K DPS parse • Endgame trial experience"
    assert healer.qualification_summary == "Endgame trial experience"


def test_recruitment_requirement_rejects_parse_threshold_for_non_dd():
    with pytest.raises(
        ValueError,
        match="minimum_parse_damage is only valid for DD requirements",
    ):
        RecruitmentRequirement(
            slot_id="tank-1",
            role=Role.TANK,
            role_label="Main Tank",
            minimum_parse_damage=165_000,
        )


def test_plan_rejects_slot_totals_that_do_not_match_party_size():
    with pytest.raises(
        ValueError,
        match="must equal party_size",
    ):
        RecruitmentPlanner().build_plan(
            party_size=12,
            real_member_count=2,
            open_role_labels=("DD 1",),
        )
