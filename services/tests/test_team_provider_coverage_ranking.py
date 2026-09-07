from minmax.build_candidate import BuildCandidate
from minmax.build_candidate_comparison import (
    BuildCandidateComparison,
    CandidateConstraint,
    ConstraintStatus,
)
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild
from services.team_prescription import (
    PrescribedRoster,
    PrescribedRosterAssignment,
    PrescriptionDimension,
    TeamPrescriptionScope,
)
from services.team_prescription_candidate_ranking import (
    PrescribedSlotCandidateEvidence,
    rank_prescribed_slot_candidates,
)
from services.team_prescription_optimizer import optimize_prescribed_roster_candidates
from services.team_provider_coverage_service import TeamProviderCoverageProfile


def _evidence(candidate_id, *, provider_id, targets, max_apps, value=130.0):
    build = PlayerBuild(
        Name=candidate_id,
        BuildName=f"{candidate_id} Build",
        Role="DD",
        EsoClass="Arcanist",
    )
    candidate = BuildCandidate.from_build(
        character_id=f"candidate:{candidate_id}",
        baseline_build_id="coverage-baseline",
        candidate_id=candidate_id,
        candidate_build=build,
        changes=(),
        candidate_source="phase13.2:test-provider-coverage",
    )
    comparison = BuildCandidateComparison(
        candidate=candidate,
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=value,
        constraints=(
            CandidateConstraint(
                name="hard constraint",
                status=ConstraintStatus.PRESERVED,
                explanation="coverage test",
            ),
        ),
    )
    return PrescribedSlotCandidateEvidence(
        comparison=comparison,
        provider_requirement_ids=(provider_id,),
        provider_coverage_profiles=(
            TeamProviderCoverageProfile(
                provider_key=provider_id,
                targets_per_application=targets,
                max_applications_per_cycle=max_apps,
            ),
        ),
    )


def _roster():
    return PrescribedRoster(
        name="Coverage Roster",
        goal="Optimization",
        scope=TeamPrescriptionScope(
            dimensions=(PrescriptionDimension.CLASS, PrescriptionDimension.BUILD)
        ),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="DD 1",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
                unresolved=("DD 1 open",),
            ),
        ),
        unresolved=("DD 1 open",),
    )


def test_banner_identity_does_not_satisfy_twelve_person_coverage_when_one_instance_caps_at_six():
    banner = _evidence(
        "banner",
        provider_id="banner",
        targets=6,
        max_apps=1,
    )

    ranking = rank_prescribed_slot_candidates(
        slot_name="DD 1",
        required_provider_requirement_ids=("banner",),
        candidates=(banner,),
        provider_required_recipients_by_id={"banner": 12},
    )

    assert ranking.recommended is None
    assert ranking.rejected[0].candidate_id == "banner"
    assert "covers 6/12 intended recipients" in ranking.rejected[0].reasons[0]


def test_roaring_two_applications_satisfy_twelve_person_coverage():
    roaring = _evidence(
        "roaring",
        provider_id="roaring_opportunist",
        targets=6,
        max_apps=2,
    )

    ranking = rank_prescribed_slot_candidates(
        slot_name="DD 1",
        required_provider_requirement_ids=("roaring_opportunist",),
        candidates=(roaring,),
        provider_required_recipients_by_id={"roaring_opportunist": 12},
    )

    assert ranking.recommended is roaring
    assert ranking.rejected == ()


def test_powerful_assault_two_applications_satisfy_twelve_person_coverage():
    pa = _evidence(
        "pa",
        provider_id="powerful_assault",
        targets=6,
        max_apps=2,
    )

    ranking = rank_prescribed_slot_candidates(
        slot_name="DD 1",
        required_provider_requirement_ids=("powerful_assault",),
        candidates=(pa,),
        provider_required_recipients_by_id={"powerful_assault": 12},
    )

    assert ranking.recommended is pa


def test_legacy_identity_only_provider_requirement_remains_backward_compatible():
    banner = _evidence(
        "banner",
        provider_id="banner",
        targets=6,
        max_apps=1,
    )

    ranking = rank_prescribed_slot_candidates(
        slot_name="DD 1",
        required_provider_requirement_ids=("banner",),
        candidates=(banner,),
    )

    assert ranking.recommended is banner


def test_declared_recipient_requirement_without_coverage_profile_is_unproven():
    evidence = _evidence(
        "plain",
        provider_id="trial_provider",
        targets=6,
        max_apps=1,
    )
    evidence = PrescribedSlotCandidateEvidence(
        comparison=evidence.comparison,
        provider_requirement_ids=evidence.provider_requirement_ids,
    )

    ranking = rank_prescribed_slot_candidates(
        slot_name="DD 1",
        required_provider_requirement_ids=("trial_provider",),
        candidates=(evidence,),
        provider_required_recipients_by_id={"trial_provider": 12},
    )

    assert ranking.recommended is None
    assert "coverage is unproven" in ranking.rejected[0].reasons[0]


def test_roster_optimizer_threads_recipient_requirement_to_candidate_ranking():
    banner = _evidence(
        "banner",
        provider_id="trial_provider",
        targets=6,
        max_apps=1,
        value=150.0,
    )
    full = _evidence(
        "full",
        provider_id="trial_provider",
        targets=6,
        max_apps=2,
        value=120.0,
    )

    result = optimize_prescribed_roster_candidates(
        roster=_roster(),
        candidate_pools={"DD 1": (banner, full)},
        provider_requirements_by_slot={"DD 1": ("trial_provider",)},
        provider_required_recipients_by_slot={
            "DD 1": {"trial_provider": 12},
        },
    )

    assert result.applied_count == 1
    assert result.final_roster.assignments[0].source_build_name == "full Build"
    rejected = result.slots[0].ranking.rejected
    assert any(row.candidate_id == "banner" for row in rejected)
