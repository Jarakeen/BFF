from __future__ import annotations

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
from services.team_provider_workload_policy_service import (
    TeamProviderWorkloadPolicy,
    TeamProviderWorkloadPolicyDimension,
    TeamProviderWorkloadPolicyPriority,
)


def _burden() -> RotationExecutionBurden:
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
    alternative_id: str,
    *,
    displacement: float = 1.0,
    ultimate_spent: float = 0.0,
    resource_costs: tuple[tuple[str, float], ...] = (("magicka", 3000.0),),
) -> TeamProviderRotationWorkload:
    return TeamProviderRotationWorkload(
        alternative_id=alternative_id,
        effect_key="major_slayer",
        duration_seconds=60.0,
        recipient_coverage_met=True,
        temporal_coverage_met=True,
        contributor_count=1,
        provider_applications=3,
        provider_applications_per_minute=3.0,
        provider_refreshes=2,
        provider_gcd_seconds=3.0,
        provider_cast_channel_seconds=0.0,
        refreshes_per_minute=2.0,
        resource_costs=resource_costs,
        ultimate_spent=ultimate_spent,
        occupied_bar_slots=(f"magrat:front:{alternative_id}",),
        primary_role_displacement_seconds=displacement,
        whole_plan_burden=_burden(),
        unresolved=(),
    )


def _candidate_result(
    *workloads: TeamProviderRotationWorkload,
    rejected: tuple[TeamProviderWorkloadCandidateRejection, ...] = (),
) -> TeamProviderWorkloadCandidateResult:
    return TeamProviderWorkloadCandidateResult(
        projections=tuple(SimpleNamespace(workload=item) for item in workloads),
        rejected=rejected,
    )


def _policy() -> TeamProviderWorkloadPolicy:
    return TeamProviderWorkloadPolicy(
        policy_id="Lokke healer support",
        encounter_key="Sunspire Lokke HM",
        role_key="Healer",
        priorities=(
            TeamProviderWorkloadPolicyPriority(
                TeamProviderWorkloadPolicyDimension.PRIMARY_ROLE_DISPLACEMENT_SECONDS
            ),
            TeamProviderWorkloadPolicyPriority(
                TeamProviderWorkloadPolicyDimension.ULTIMATE_SPENT
            ),
        ),
    )


def test_candidate_render_applies_policy_and_explains_scope_and_selection():
    protects_role = _workload(
        "protects role",
        displacement=0.25,
        ultimate_spent=200.0,
        resource_costs=(("magicka", 5000.0),),
    )
    saves_ultimate = _workload(
        "saves ultimate",
        displacement=1.5,
        ultimate_spent=0.0,
        resource_costs=(("magicka", 1000.0),),
    )

    rendered = TeamProviderWorkloadExplanationService.render_candidate_result(
        _candidate_result(protects_role, saves_ultimate),
        policy=_policy(),
    )

    assert "PROTECTS ROLE • major_slayer • FRONTIER • SELECTED" in rendered
    assert "SAVES ULTIMATE • major_slayer • FRONTIER" in rendered
    assert "SAVES ULTIMATE • major_slayer • FRONTIER • SELECTED" not in rendered
    assert "POLICY • Lokke healer support" in rendered
    assert "encounter=sunspire_lokke_hm" in rendered
    assert "role=healer" in rendered
    assert "selected protects role; considered protects role, saves ultimate" in rendered
    assert (
        "primary_role_displacement_seconds: kept protects role at 0.25; "
        "deprioritized saves ultimate=1.5"
    ) in rendered
    assert "Encounter / role policy selected this retained frontier plan." in rendered
    assert "considered this retained frontier tradeoff" in rendered
    assert "Encounter / role policy is still required" not in rendered
    assert "not weighted exchange rates" in rendered


def test_policy_render_keeps_unresolved_tie_explicit():
    alpha = _workload("alpha", displacement=0.5, ultimate_spent=100.0)
    beta = _workload("beta", displacement=0.5, ultimate_spent=100.0)

    rendered = TeamProviderWorkloadExplanationService.render_candidate_result(
        _candidate_result(alpha, beta),
        policy=_policy(),
    )

    assert "ALPHA • major_slayer • FRONTIER • SELECTED" in rendered
    assert "BETA • major_slayer • FRONTIER • SELECTED" in rendered
    assert "selected alpha, beta; considered alpha, beta" in rendered
    assert "Policy leaves these frontier alternatives tied." in rendered


def test_candidate_render_without_policy_preserves_frontier_boundary():
    fewer_role_seconds = _workload(
        "fewer role seconds",
        displacement=0.25,
        ultimate_spent=200.0,
    )
    saves_ultimate = _workload(
        "saves ultimate",
        displacement=1.5,
        ultimate_spent=0.0,
    )

    rendered = TeamProviderWorkloadExplanationService.render_candidate_result(
        _candidate_result(fewer_role_seconds, saves_ultimate)
    )

    assert "Encounter / role policy is still required" in rendered
    assert "• SELECTED" not in rendered
    assert "POLICY •" not in rendered


def test_policy_render_explains_single_frontier_survivor_without_fake_tiebreak():
    only = _workload("only viable")

    rendered = TeamProviderWorkloadExplanationService.render_candidate_result(
        _candidate_result(only),
        policy=_policy(),
    )

    assert "ONLY VIABLE • major_slayer • FRONTIER • SELECTED" in rendered
    assert "selected only viable; considered only viable" in rendered
    assert "Only one frontier alternative remained in this scope." in rendered


def test_policy_render_does_not_promote_rejected_candidate():
    rejection = TeamProviderWorkloadCandidateRejection(
        alternative_id="missing rotation",
        effect_key="major_slayer",
        blockers=("no exact rotation plan is attached",),
    )

    rendered = TeamProviderWorkloadExplanationService.render_candidate_result(
        _candidate_result(rejected=(rejection,)),
        policy=_policy(),
    )

    assert "MISSING ROTATION • major_slayer • REJECTED" in rendered
    assert "MISSING ROTATION • major_slayer • REJECTED • SELECTED" not in rendered
    assert "No frontier alternatives were available for policy selection." in rendered
    assert "no exact rotation plan is attached" in rendered
