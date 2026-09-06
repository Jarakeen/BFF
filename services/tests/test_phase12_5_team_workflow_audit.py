from __future__ import annotations

from models.build_model import BuildRoster, PlayerBuild
from models.roster_model import RosterMember
from services.generated_roster_plan_service import GeneratedRosterPlan, GeneratedRosterPlanSlot
from services.phase12_5_team_workflow_audit import Phase125TeamWorkflowAuditService


def _build() -> PlayerBuild:
    return PlayerBuild(
        Name="Magrat",
        Gamertag="@keen",
        BuildName="GH Healer",
        EsoClass="Warden",
        Role="Healer",
    )


def _member() -> RosterMember:
    return RosterMember(
        Id=1,
        PlayerName="@keen",
        CharacterName="Magrat",
        EsoClass="Warden",
        PrimaryRole="Healer",
        Team="Other Team, GH Prog",
    )


def _plan() -> GeneratedRosterPlan:
    return GeneratedRosterPlan(
        plan_id=7,
        name="GH Prog",
        goal="Cloudrest",
        difficulty="Veteran Hardmode",
        slots=(
            GeneratedRosterPlanSlot(
                slot_name="Healer 1",
                kind="saved",
                player_name="@keen",
                character_name="Magrat",
                eso_class="Warden",
                build_name="GH Healer",
                role="Healer",
                source_kind="saved_build",
                source_name="Saved Roster Build",
                gear_sets=("Spell Power Cure",),
                skills=("Combat Prayer",),
                mundus="The Atronach",
                unresolved="Exact encounter bar changes unresolved.",
            ),
            GeneratedRosterPlanSlot(
                slot_name="Damage 1",
                kind="prescribed_recruit",
                player_name="Recruitment Needed",
                character_name="",
                eso_class="Arcanist",
                build_name="Arcanist DD",
                role="Damage Dealer",
                source_kind="reference_template",
                candidate_id="template:arc-dd",
                unresolved="Exact traits unresolved.",
            ),
        ),
    )


def _prescription():
    return {
        "slot_name": "Healer 1",
        "role": "Healer",
        "eso_class": "Warden",
        "build_name": "Brittle Warden Healer",
        "source_kind": "reference_template",
        "source_name": "Healer Catalog",
        "source_url": "https://example.invalid",
        "candidate_id": "template:brittle-warden",
        "gear_sets": ["Serpent's Disdain", "Pillager's Profit"],
        "skills": ["Combat Prayer", "Frost Cloak"],
        "mundus": "The Atronach",
        "unresolved": "Exact slots unresolved.",
    }


def test_phase12_5_audit_accepts_real_saved_assignment_and_explicit_recruit_boundary() -> None:
    result = Phase125TeamWorkflowAuditService.audit(
        team_name="GH Prog",
        registered_team_names=("GH Prog",),
        plan=_plan(),
        builds=BuildRoster(Members=[_build()]),
        roster_members=(_member(),),
        recruit_prescriptions={"Healer 1": _prescription()},
    )

    assert result.passed is True
    assert result.slot_count == 2
    assert result.saved_slot_count == 1
    assert result.recruit_slot_count == 1
    assert result.exact_saved_assignment_count == 1
    assert result.adopted_prescription_count == 1
    assert result.unresolved_count == 2
    assert result.problems == ()
    assert any("later encounter evaluation" in value for value in result.boundaries)
    assert any("raid outcome" in value for value in result.boundaries)


def test_phase12_5_audit_fails_when_exact_saved_build_is_lost() -> None:
    result = Phase125TeamWorkflowAuditService.audit(
        team_name="GH Prog",
        registered_team_names=("GH Prog",),
        plan=_plan(),
        builds=BuildRoster(Members=[PlayerBuild(Name="Magrat", BuildName="DF Healer")]),
        roster_members=(_member(),),
    )

    assert result.passed is False
    assert result.exact_saved_assignment_count == 0
    assert any("cannot be resolved" in problem for problem in result.problems)


def test_phase12_5_audit_fails_when_team_membership_is_lost() -> None:
    member = _member()
    member.Team = "Other Team"

    result = Phase125TeamWorkflowAuditService.audit(
        team_name="GH Prog",
        registered_team_names=("GH Prog",),
        plan=_plan(),
        builds=BuildRoster(Members=[_build()]),
        roster_members=(member,),
    )

    assert result.passed is False
    assert any("not a member of named team" in problem for problem in result.problems)


def test_phase12_5_audit_detects_lost_structured_adoption_evidence() -> None:
    incomplete = _prescription()
    del incomplete["candidate_id"]

    result = Phase125TeamWorkflowAuditService.audit(
        team_name="GH Prog",
        registered_team_names=("GH Prog",),
        plan=_plan(),
        builds=BuildRoster(Members=[_build()]),
        roster_members=(_member(),),
        recruit_prescriptions={"Healer 1": incomplete},
    )

    assert result.passed is False
    assert any("candidate_id" in problem for problem in result.problems)


def test_phase12_5_audit_detects_duplicate_chairs() -> None:
    plan = _plan()
    duplicate = GeneratedRosterPlan(
        plan_id=plan.plan_id,
        name=plan.name,
        goal=plan.goal,
        difficulty=plan.difficulty,
        slots=(plan.slots[0], plan.slots[0]),
    )

    result = Phase125TeamWorkflowAuditService.audit(
        team_name="GH Prog",
        registered_team_names=("GH Prog",),
        plan=duplicate,
        builds=BuildRoster(Members=[_build()]),
        roster_members=(_member(),),
    )

    assert result.passed is False
    assert any("Duplicate generated chair" in problem for problem in result.problems)
