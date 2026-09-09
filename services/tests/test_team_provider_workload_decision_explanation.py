from types import SimpleNamespace

from services.rotation_execution_burden_service import RotationExecutionBurden
from services.team_provider_rotation_workload_service import TeamProviderRotationWorkload
from services.team_provider_workload_candidate_service import (
    TeamProviderWorkloadCandidateRejection,
    TeamProviderWorkloadCandidateResult,
)
from services.team_provider_workload_explanation_service import (
    TeamProviderWorkloadExplanationService,
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
    applications=3,
    gcd_seconds=3.0,
    resource_costs=(("magicka", 3000.0),),
    displacement=0.75,
    temporal_coverage_met=True,
):
    return TeamProviderRotationWorkload(
        alternative_id=alternative_id,
        effect_key="minor_berserk",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=temporal_coverage_met,
        contributor_count=1,
        provider_applications=applications,
        provider_applications_per_minute=float(applications),
        provider_refreshes=max(0, applications - 1),
        provider_gcd_seconds=gcd_seconds,
        provider_cast_channel_seconds=0.0,
        refreshes_per_minute=float(max(0, applications - 1)),
        resource_costs=resource_costs,
        ultimate_spent=0.0,
        occupied_bar_slots=("magrat:front:provider",),
        primary_role_displacement_seconds=displacement,
        whole_plan_burden=_burden(),
        unresolved=(),
    )


def _result(*workloads, rejected=()):
    return TeamProviderWorkloadCandidateResult(
        projections=tuple(SimpleNamespace(workload=item) for item in workloads),
        rejected=rejected,
    )


def test_candidate_panel_labels_frontier_and_dominated_without_policy_winner():
    efficient = _workload(
        "efficient",
        applications=2,
        gcd_seconds=2.0,
        resource_costs=(("magicka", 1800.0),),
        displacement=0.5,
    )
    expensive = _workload("expensive")

    rendered = TeamProviderWorkloadExplanationService.render_candidate_result(
        _result(efficient, expensive)
    )

    assert "EFFICIENT • minor_berserk • FRONTIER" in rendered
    assert "EXPENSIVE • minor_berserk • DOMINATED" in rendered
    assert "Dominated by: efficient." in rendered
    assert "magicka spend: 1800 vs 3000" in rendered
    assert "Encounter / role policy is still required" in rendered


def test_candidate_panel_keeps_coverage_failure_distinct_from_dominance():
    blocked = _workload(
        "partial",
        applications=1,
        gcd_seconds=1.0,
        resource_costs=(),
        displacement=0.0,
        temporal_coverage_met=False,
    )

    rendered = TeamProviderWorkloadExplanationService.render_candidate_result(
        _result(blocked)
    )

    assert "PARTIAL • minor_berserk • BLOCKED" in rendered
    assert "temporal coverage requirement is not met" in rendered
    assert "Dominated by:" not in rendered


def test_candidate_panel_keeps_projection_rejection_distinct_from_blocked_workload():
    rejection = TeamProviderWorkloadCandidateRejection(
        alternative_id="missing rotation",
        effect_key="minor_berserk",
        blockers=("no exact rotation plan is attached",),
    )

    rendered = TeamProviderWorkloadExplanationService.render_candidate_result(
        _result(rejected=(rejection,))
    )

    assert "MISSING ROTATION • minor_berserk • REJECTED" in rendered
    assert "Candidate not projected:" in rendered
    assert "no exact rotation plan is attached" in rendered
    assert "Provider work:" not in rendered
