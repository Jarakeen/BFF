from types import SimpleNamespace

from services.rotation_execution_burden_service import RotationExecutionBurden
from services.team_provider_rotation_workload_service import TeamProviderRotationWorkload
from services.team_provider_workload_candidate_service import (
    TeamProviderWorkloadCandidateRejection,
    TeamProviderWorkloadCandidateResult,
)
from services.team_provider_workload_decision_service import (
    TeamProviderWorkloadDecisionService,
    TeamProviderWorkloadDecisionStatus,
)


def _burden():
    return RotationExecutionBurden(
        total_actions=10,
        skill_casts=10,
        ultimate_casts=0,
        light_attacks=0,
        heavy_attacks=0,
        potions=0,
        bar_swaps=0,
        waits=0,
    )


def _workload(
    alternative_id,
    *,
    effect_key="minor_berserk",
    duration_seconds=60.0,
    applications=3,
    gcd_seconds=3.0,
    resource_costs=(("magicka", 3000.0),),
    displacement=0.75,
    recipient_coverage_met=True,
    temporal_coverage_met=True,
    unresolved=(),
):
    return TeamProviderRotationWorkload(
        alternative_id=alternative_id,
        effect_key=effect_key,
        duration_seconds=duration_seconds,
        recipient_coverage_met=recipient_coverage_met,
        temporal_coverage_met=temporal_coverage_met,
        contributor_count=1,
        provider_applications=applications,
        provider_applications_per_minute=applications * 60.0 / duration_seconds,
        provider_refreshes=max(0, applications - 1),
        provider_gcd_seconds=gcd_seconds,
        provider_cast_channel_seconds=0.0,
        refreshes_per_minute=max(0, applications - 1) * 60.0 / duration_seconds,
        resource_costs=resource_costs,
        ultimate_spent=0.0,
        occupied_bar_slots=("magrat:front:provider",),
        primary_role_displacement_seconds=displacement,
        whole_plan_burden=_burden(),
        unresolved=unresolved,
    )


def _result(*workloads, rejected=()):
    return TeamProviderWorkloadCandidateResult(
        projections=tuple(SimpleNamespace(workload=item) for item in workloads),
        rejected=rejected,
    )


def test_classifies_frontier_and_dominated_candidates_with_reason():
    efficient = _workload(
        "efficient",
        applications=2,
        gcd_seconds=2.0,
        resource_costs=(("magicka", 1800.0),),
        displacement=0.5,
    )
    expensive = _workload("expensive")

    result = TeamProviderWorkloadDecisionService.analyze(_result(efficient, expensive))

    assert tuple(item.alternative_id for item in result.frontier) == ("efficient",)
    dominated = result.dominated[0]
    assert dominated.alternative_id == "expensive"
    assert dominated.status is TeamProviderWorkloadDecisionStatus.DOMINATED
    assert dominated.dominated_by == ("efficient",)
    assert any("provider applications" in item for item in dominated.improvements)
    assert any("magicka spend" in item for item in dominated.improvements)


def test_keeps_real_tradeoff_candidates_on_frontier():
    fewer_casts = _workload(
        "fewer casts",
        applications=2,
        gcd_seconds=2.0,
        resource_costs=(("magicka", 5000.0),),
    )
    cheaper_casts = _workload(
        "cheaper casts",
        applications=3,
        gcd_seconds=3.0,
        resource_costs=(("magicka", 1800.0),),
    )

    result = TeamProviderWorkloadDecisionService.analyze(
        _result(fewer_casts, cheaper_casts)
    )

    assert tuple(item.alternative_id for item in result.frontier) == (
        "fewer casts",
        "cheaper casts",
    )
    assert result.dominated == ()


def test_groups_different_effects_and_horizons_before_frontier_evaluation():
    short_minor = _workload("short minor", duration_seconds=30.0)
    long_minor = _workload("long minor", duration_seconds=60.0)
    major = _workload("major", effect_key="major_slayer", duration_seconds=60.0)

    result = TeamProviderWorkloadDecisionService.analyze(
        _result(short_minor, long_minor, major)
    )

    assert tuple(item.alternative_id for item in result.frontier) == (
        "major",
        "short minor",
        "long minor",
    )
    assert result.dominated == ()


def test_projected_coverage_failure_is_blocked_not_dominated():
    blocked = _workload(
        "partial coverage",
        applications=1,
        gcd_seconds=1.0,
        resource_costs=(),
        displacement=0.0,
        temporal_coverage_met=False,
    )
    viable = _workload("viable")

    result = TeamProviderWorkloadDecisionService.analyze(_result(blocked, viable))

    blocked_decision = next(
        item for item in result.blocked if item.alternative_id == "partial coverage"
    )
    assert blocked_decision.status is TeamProviderWorkloadDecisionStatus.BLOCKED
    assert blocked_decision.blockers == (
        "temporal coverage requirement is not met",
    )


def test_blocked_candidate_preserves_unresolved_and_coverage_reasons():
    blocked = _workload(
        "double blocked",
        recipient_coverage_met=False,
        temporal_coverage_met=False,
        unresolved=("canonical resource cost is unresolved",),
    )

    result = TeamProviderWorkloadDecisionService.analyze(_result(blocked))

    decision = result.blocked[0]
    assert decision.blockers == (
        "canonical resource cost is unresolved",
        "recipient coverage requirement is not met",
        "temporal coverage requirement is not met",
    )


def test_projection_rejection_remains_distinct_from_workload_blocker():
    rejection = TeamProviderWorkloadCandidateRejection(
        alternative_id="missing rotation",
        effect_key="minor_berserk",
        blockers=("no exact rotation plan is attached",),
    )

    result = TeamProviderWorkloadDecisionService.analyze(_result(rejected=(rejection,)))

    assert len(result.blocked) == 1
    decision = result.blocked[0]
    assert decision.status is TeamProviderWorkloadDecisionStatus.REJECTED
    assert decision.duration_seconds is None
    assert decision.workload is None
    assert decision.blockers == ("no exact rotation plan is attached",)
