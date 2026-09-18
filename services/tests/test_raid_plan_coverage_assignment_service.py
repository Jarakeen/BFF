from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember
from services.raid_plan_coverage_assignment_service import (
    RaidPlanCoverageAssignmentService,
)
from services.raid_plan_coverage_scope_service import RaidPlanCoverageScopeService
from services.saved_build_capability_service import RaidCoverageSnapshot


def _scope(*members: RaidPlanMember):
    plan = RaidPlan(
        plan_id="plan",
        trial_id="rockgrove",
        name="Plan",
        members=tuple(members),
    )
    saved = tuple(
        PlayerBuild(
            Gamertag=member.gamertag,
            Name=member.character_name or "",
            BuildName=member.selected_build_name or "",
        )
        for member in members
        if member.selected_build_name
    )
    return RaidPlanCoverageScopeService().compose(
        raid_plan=plan,
        saved_builds=saved,
        coverage_effect_names=("Major Courage",),
    )


def _snapshot(*, static=(), conditional=()):
    if static:
        state = "available"
    elif conditional:
        state = "conditional"
    else:
        state = "not_found"
    return RaidCoverageSnapshot(
        {"Major Courage": state},
        {"Major Courage": list(static)},
        {"Major Courage": list(conditional)},
    )


def test_explicit_assigned_provider_is_confirmed_from_static_evidence() -> None:
    scope = _scope(
        RaidPlanMember(
            seat_id="dd-1",
            gamertag="Wolf",
            character_name="Werewolf DD",
            selected_build_name="Courage Wolf",
            primary_assignment="Major Courage",
        )
    )

    review = RaidPlanCoverageAssignmentService().review(
        effect_name="Major Courage",
        scope=scope,
        snapshot=_snapshot(static=("Werewolf DD",)),
    )

    assert review.state == "assigned_supported"
    assert review.supported_primary == ("Werewolf DD",)
    assert review.label == "Assigned • Supported"


def test_assignment_is_not_claimed_when_some_other_build_has_the_effect() -> None:
    scope = _scope(
        RaidPlanMember(
            seat_id="dd-1",
            gamertag="Wolf",
            character_name="Werewolf DD",
            selected_build_name="Courage Wolf",
            primary_assignment="Major Courage",
        ),
        RaidPlanMember(
            seat_id="healer-1",
            gamertag="Healer",
            character_name="Healer Character",
            selected_build_name="Healer Build",
        ),
    )

    review = RaidPlanCoverageAssignmentService().review(
        effect_name="Major Courage",
        scope=scope,
        snapshot=_snapshot(static=("Healer Character",)),
    )

    assert review.state == "assigned_unproven"
    assert review.unsupported_primary == ("Werewolf DD",)


def test_planned_gear_conditional_evidence_can_confirm_assigned_provider_conditionally() -> None:
    scope = _scope(
        RaidPlanMember(
            seat_id="dd-1",
            gamertag="Wolf",
            character_name="Werewolf DD",
            primary_assignment="Major Courage",
            planned_gear_sets=("Some Courage Set",),
        )
    )

    review = RaidPlanCoverageAssignmentService().review(
        effect_name="Major Courage",
        scope=scope,
        snapshot=_snapshot(
            conditional=("Werewolf DD [planned: Some Courage Set]",)
        ),
    )

    assert review.state == "assigned_conditional"
    assert review.conditional_primary == ("Werewolf DD",)


def test_unassigned_existing_source_is_not_mislabeled_as_a_gap() -> None:
    scope = _scope(
        RaidPlanMember(
            seat_id="healer-1",
            gamertag="Healer",
            character_name="Healer Character",
            selected_build_name="Healer Build",
        )
    )

    review = RaidPlanCoverageAssignmentService().review(
        effect_name="Major Courage",
        scope=scope,
        snapshot=_snapshot(static=("Healer Character",)),
    )

    assert review.state == "unassigned_available"
    assert review.label == "Source found • Unassigned"


def test_multiple_primary_assignments_are_flagged_without_treating_backup_as_duplicate() -> None:
    scope = _scope(
        RaidPlanMember(
            seat_id="dd-1",
            gamertag="One",
            character_name="One",
            selected_build_name="Build One",
            primary_assignment="Major Courage",
        ),
        RaidPlanMember(
            seat_id="dd-2",
            gamertag="Two",
            character_name="Two",
            selected_build_name="Build Two",
            primary_assignment="Major Courage",
        ),
        RaidPlanMember(
            seat_id="healer-1",
            gamertag="Backup",
            character_name="Backup",
            selected_build_name="Backup Build",
            secondary_assignment="Major Courage",
        ),
    )

    review = RaidPlanCoverageAssignmentService().review(
        effect_name="Major Courage",
        scope=scope,
        snapshot=_snapshot(static=("One", "Two", "Backup")),
    )

    assert review.duplicate_primary is True
    assert review.label == "Assigned • Supported • Duplicate primary"


def test_no_assignment_and_no_evidence_is_a_gap() -> None:
    scope = _scope()

    review = RaidPlanCoverageAssignmentService().review(
        effect_name="Major Courage",
        scope=scope,
        snapshot=_snapshot(),
    )

    assert review.state == "gap"
    assert review.needs_attention is True
