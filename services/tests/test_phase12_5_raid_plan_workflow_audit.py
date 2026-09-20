from __future__ import annotations

from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember
from models.roster_model import RosterMember
from services.phase12_5_raid_plan_workflow_audit import (
    Phase125RaidPlanWorkflowAuditService,
)


def _build() -> PlayerBuild:
    return PlayerBuild(
        Name="Magrat",
        Gamertag="@keen",
        BuildName="GH Healer",
        EsoClass="Warden",
        Role="Healer",
        PlayerId="player-1",
        CharacterId="character-1",
        BuildId="build-1",
    )


def _roster_member() -> RosterMember:
    return RosterMember(
        Id=7,
        PlayerName="@keen",
        CharacterName="Magrat",
        EsoClass="Warden",
        PrimaryRole="Healer",
        Team="Performance Mode",
        CanonicalPlayerId="player-1",
        CanonicalCharacterId="character-1",
    )


def _plan(*, member: RaidPlanMember | None = None) -> RaidPlan:
    return RaidPlan(
        plan_id="pm-cloudrest",
        trial_id="cloudrest",
        name="Performance Mode — Cloudrest",
        team_name="Performance Mode",
        difficulty="Veteran Hardmode",
        members=(
            member
            or RaidPlanMember(
                seat_id="healer-1",
                gamertag="@keen",
                roster_member_id=7,
                player_id="player-1",
                character_id="character-1",
                character_name="Magrat",
                role="Healer",
                eso_class="Warden",
                selected_build_id="build-1",
                selected_build_name="GH Healer",
                planned_gear_sets=("Roaring Opportunist", "Jorvuld's Guidance"),
                primary_assignment="Major Slayer",
                assignment_source="Roaring Opportunist",
                comp_locked_fields=("player", "class", "role", "build", "gear"),
                notes="Exact portal timing unresolved.",
            ),
        ),
    )


def test_phase12_5_canonical_audit_accepts_exact_identity_and_constraints() -> None:
    result = Phase125RaidPlanWorkflowAuditService().audit(
        raid_plan=_plan(),
        saved_builds=(_build(),),
        roster_members=(_roster_member(),),
    )

    assert result.passed is True
    assert result.chair_count == 1
    assert result.assigned_player_count == 1
    assert result.recruit_count == 0
    assert result.selected_build_count == 1
    assert result.resolved_build_count == 1
    assert result.team_identity_preserved is True
    assert result.player_identity_preserved is True
    assert result.character_identity_preserved is True
    assert result.build_identity_preserved is True
    assert result.class_constraints_preserved is True
    assert result.role_constraints_preserved is True
    assert result.gear_constraints_preserved is True
    assert result.provider_assignment_preserved is True
    assert result.unresolved_state_preserved is True
    assert result.unresolved_chair_count == 1
    assert result.problems == ()


def test_phase12_5_canonical_audit_preserves_open_recruit_without_fake_identity() -> None:
    member = RaidPlanMember(
        seat_id="dd-7",
        role="DD",
        eso_class="Arcanist",
        planned_gear_sets=("Coral Riptide",),
        planned_skills=("Fatecarver",),
        build_source_kind="reference_template",
        build_source_name="Reviewed DD template",
        candidate_id="template:arc-dd",
        notes="Exact traits unresolved.",
    )

    result = Phase125RaidPlanWorkflowAuditService().audit(
        raid_plan=_plan(member=member),
        saved_builds=(_build(),),
        roster_members=(_roster_member(),),
    )

    assert result.passed is True
    assert result.recruit_count == 1
    assert result.assigned_player_count == 0
    assert result.recruit_state_preserved is True
    assert result.unresolved_state_preserved is True
    assert any("recruit/open chair remains explicit" in value for value in result.boundaries)


def test_phase12_5_canonical_audit_fails_closed_on_stable_build_identity_drift() -> None:
    build = _build()
    build.BuildId = "different-build"

    result = Phase125RaidPlanWorkflowAuditService().audit(
        raid_plan=_plan(),
        saved_builds=(build,),
        roster_members=(_roster_member(),),
    )

    assert result.passed is False
    assert result.build_identity_preserved is False
    assert any("stable BuildId" in problem for problem in result.problems)


def test_phase12_5_canonical_audit_fails_on_class_or_role_drift() -> None:
    build = _build()
    build.EsoClass = "Templar"
    build.Role = "DD"

    result = Phase125RaidPlanWorkflowAuditService().audit(
        raid_plan=_plan(),
        saved_builds=(build,),
        roster_members=(_roster_member(),),
    )

    assert result.passed is False
    assert result.class_constraints_preserved is False
    assert result.role_constraints_preserved is False


def test_phase12_5_canonical_audit_fails_when_recruit_carries_saved_identity() -> None:
    member = RaidPlanMember(
        seat_id="dd-7",
        role="DD",
        eso_class="Arcanist",
        selected_build_id="build-ghost",
        selected_build_name="Ghost Build",
    )

    result = Phase125RaidPlanWorkflowAuditService().audit(
        raid_plan=_plan(member=member),
        saved_builds=(_build(),),
        roster_members=(_roster_member(),),
    )

    assert result.passed is False
    assert result.recruit_state_preserved is False
    assert any("without an assigned player" in problem for problem in result.problems)


def test_phase12_5_canonical_audit_requires_provenance_for_non_saved_candidate() -> None:
    member = RaidPlanMember(
        seat_id="dd-7",
        role="DD",
        eso_class="Arcanist",
        build_source_kind="reference_template",
    )

    result = Phase125RaidPlanWorkflowAuditService().audit(
        raid_plan=_plan(member=member),
        saved_builds=(_build(),),
        roster_members=(_roster_member(),),
    )

    assert result.passed is False
    assert result.unresolved_state_preserved is False
    assert any("lost its structured provenance" in problem for problem in result.problems)


def test_phase12_5_canonical_audit_rejects_meaningless_locked_gear() -> None:
    member = RaidPlanMember(
        seat_id="dd-7",
        role="DD",
        eso_class="Arcanist",
        comp_locked_fields=("gear",),
    )

    result = Phase125RaidPlanWorkflowAuditService().audit(
        raid_plan=_plan(member=member),
        saved_builds=(_build(),),
        roster_members=(_roster_member(),),
    )

    assert result.passed is False
    assert result.gear_constraints_preserved is False
    assert any("gear is locked" in problem for problem in result.problems)
