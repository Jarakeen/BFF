from __future__ import annotations

from pathlib import Path

import pytest

from models.build_model import BuildRoster, PlayerBuild
from models.roster_model import RosterMember
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.generated_roster_plan_service import (
    GeneratedRosterPlanService,
    GeneratedRosterPlanSlot,
)
from services.roster_recruit_adoption_service import RosterRecruitAdoptionService
from services.roster_service import RosterService


def _services(tmp_path: Path):
    db = EsoDatabase(tmp_path / "eso.db")
    builds = BuildService(tmp_path / "builds.json")
    plans = GeneratedRosterPlanService(db)
    roster = RosterService(db)
    adoption = RosterRecruitAdoptionService(builds=builds, plans=plans, roster=roster)
    return builds, plans, roster, adoption


def _member(roster: RosterService) -> int:
    return roster.create_member(
        RosterMember(
            PlayerName="@keen",
            CharacterName="Magrat",
            EsoClass="Warden",
            PrimaryRole="Healer",
            Team="Other Team",
        )
    )


def _build(name: str = "DF Healer") -> PlayerBuild:
    build = PlayerBuild(
        Name="Magrat",
        Gamertag="@keen",
        BuildName=name,
        EsoClass="Warden",
        Role="Healer",
        Mundus="The Ritual",
    )
    build.Armor["Head"]["Set"] = "Spell Power Cure"
    build.FrontBarSkills[0] = "Combat Prayer"
    return build


def _recruit_plan(plans: GeneratedRosterPlanService):
    return plans.save_plan(
        name="GH Prog",
        goal="Cloudrest",
        difficulty="Veteran Hardmode",
        slots=(
            GeneratedRosterPlanSlot(
                slot_name="Healer 1",
                kind="prescribed_recruit",
                player_name="Recruitment Needed",
                character_name="",
                eso_class="Warden",
                build_name="Brittle Warden Healer",
                role="Healer",
                source_kind="reference_template",
                source_name="Healer Catalog",
                source_url="https://example.invalid/healer",
                candidate_id="template:brittle-warden",
                gear_sets=("Serpent's Disdain", "Pillager's Profit"),
                skills=("Combat Prayer", "Frost Cloak"),
                mundus="The Atronach",
                unresolved="Exact gear slots and skill bar placement unresolved.",
            ),
        ),
    )


def test_assign_existing_build_preserves_original_prescription_and_team_identity(tmp_path: Path) -> None:
    builds, plans, roster, adoption = _services(tmp_path)
    member_id = _member(roster)
    builds.save(BuildRoster(Members=[_build()]))
    _recruit_plan(plans)

    result = adoption.assign_existing_build(
        plan_name="GH Prog",
        slot_name="Healer 1",
        member_id=member_id,
        build_name="DF Healer",
    )

    slot = result.slots[0]
    assert slot.kind == "saved"
    assert slot.player_name == "@keen"
    assert slot.character_name == "Magrat"
    assert slot.build_name == "DF Healer"
    assert slot.source_kind == "saved_build"
    assert "Spell Power Cure" in slot.gear_sets

    evidence = adoption.prescription_evidence("GH Prog", "Healer 1")
    assert evidence is not None
    assert evidence["candidate_id"] == "template:brittle-warden"
    assert evidence["gear_sets"] == ["Serpent's Disdain", "Pillager's Profit"]
    assert evidence["skills"] == ["Combat Prayer", "Frost Cloak"]
    assert evidence["mundus"] == "The Atronach"

    updated_member = roster.get_member(member_id)
    assert updated_member is not None
    assert set(part.strip() for part in updated_member.Team.split(",")) == {
        "Other Team",
        "GH Prog",
    }


def test_adopt_prescribed_setup_creates_new_build_without_mutating_base(tmp_path: Path) -> None:
    builds, plans, roster, adoption = _services(tmp_path)
    member_id = _member(roster)
    base = _build()
    builds.save(BuildRoster(Members=[base]))
    _recruit_plan(plans)

    result = adoption.adopt_prescribed_setup(
        plan_name="GH Prog",
        slot_name="Healer 1",
        member_id=member_id,
        base_build_name="DF Healer",
        new_build_name="GH Healer",
    )

    saved = builds.load().Members
    by_name = {build.BuildName: build for build in saved}
    assert set(by_name) >= {"DF Healer", "GH Healer"}
    assert by_name["DF Healer"].Mundus == "The Ritual"
    assert by_name["GH Healer"].Mundus == "The Atronach"

    assert by_name["GH Healer"].Armor["Head"]["Set"] == "Spell Power Cure"
    assert "Serpent's Disdain" not in {
        values.get("Set", "") for values in by_name["GH Healer"].Armor.values()
    }
    assert by_name["GH Healer"].FrontBarSkills[0] == "Combat Prayer"
    assert "Frost Cloak" not in by_name["GH Healer"].FrontBarSkills

    slot = result.slots[0]
    assert slot.kind == "saved"
    assert slot.build_name == "GH Healer"
    assert "exact gear slots" in slot.unresolved.lower()

    evidence = adoption.prescription_evidence("GH Prog", "Healer 1")
    assert evidence is not None
    assert evidence["gear_sets"] == ["Serpent's Disdain", "Pillager's Profit"]
    assert evidence["skills"] == ["Combat Prayer", "Frost Cloak"]


def test_adopt_prescribed_setup_rejects_class_mismatch(tmp_path: Path) -> None:
    builds, plans, roster, adoption = _services(tmp_path)
    member_id = _member(roster)
    wrong = _build()
    wrong.EsoClass = "Templar"
    builds.save(BuildRoster(Members=[wrong]))
    _recruit_plan(plans)

    with pytest.raises(ValueError, match="requires Warden"):
        adoption.adopt_prescribed_setup(
            plan_name="GH Prog",
            slot_name="Healer 1",
            member_id=member_id,
            base_build_name="DF Healer",
            new_build_name="GH Healer",
        )


def test_adoption_refuses_to_overwrite_an_existing_build_name(tmp_path: Path) -> None:
    builds, plans, roster, adoption = _services(tmp_path)
    member_id = _member(roster)
    builds.save(BuildRoster(Members=[_build(), _build("GH Healer")]))
    _recruit_plan(plans)

    with pytest.raises(ValueError, match="already has a build"):
        adoption.adopt_prescribed_setup(
            plan_name="GH Prog",
            slot_name="Healer 1",
            member_id=member_id,
            base_build_name="DF Healer",
            new_build_name="GH Healer",
        )


def test_recruit_adoption_ui_keeps_encounter_future_boundary_explicit() -> None:
    source = Path("ui/roster_recruit_adoption_support.py").read_text(encoding="utf-8")
    details = Path("ui/roster_recruit_prescription_details_support.py").read_text(
        encoding="utf-8"
    )
    installer = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(
        encoding="utf-8"
    )

    assert 'QPushButton("Assign Recruit")' in source
    assert '"Use existing saved build"' in source
    assert '"Create new draft from prescribed setup"' in source
    assert "Original recruit prescription preserved for later encounter evaluation" in source
    assert "Gear-set lists and observed abilities are kept as structured prescription evidence" in source
    assert '"ORIGINAL RECRUIT PRESCRIPTION"' in details
    assert '"ENCOUNTER BOUNDARY"' in details
    assert "service.prescription_evidence(plan.name, slot.slot_name)" in details
    assert "install_roster_recruit_adoption()" in installer
    assert "install_roster_recruit_prescription_details()" in installer
