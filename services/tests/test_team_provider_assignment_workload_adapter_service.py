from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.encounter_provider_candidate import (
    ProviderCandidate,
    ProviderCandidateStatus,
)
from services.rotation_assignment_effect_obligation_service import (
    RotationAssignmentEffectPolicy,
)
from services.team_provider_assignment_workload_adapter_service import (
    TeamProviderAssignedWorkloadPolicy,
    TeamProviderAssignmentWorkloadAdapterService,
)


def _provider(member_id="magrat", character="Magrat", build="DF Healer"):
    return ProviderCandidate(
        requirement_id="major_slayer_provider",
        encounter_id="lokke_hm",
        requirement_type="major_slayer",
        member_id=member_id,
        character_name=character,
        build_name=build,
        status=ProviderCandidateStatus.VIABLE,
        evidence_sources=("saved build capability",),
    )


def _assignment(*providers, status=ProviderAssignmentStatus.ASSIGNED):
    return ProviderAssignment(
        requirement_id="major_slayer_provider",
        encounter_id="lokke_hm",
        requirement_type="major_slayer",
        status=status,
        primary_providers=tuple(providers) if status is ProviderAssignmentStatus.ASSIGNED else (),
        backup_providers=tuple(providers) if status is not ProviderAssignmentStatus.ASSIGNED else (),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="explicit test assignment",
    )


def _effect_policy():
    return RotationAssignmentEffectPolicy(
        requirement_id="major_slayer_provider",
        encounter_id="lokke_hm",
        requirement_type="major_slayer",
        effect_name="Major Slayer",
        source_skill_name="Aggressive Horn",
        minimum_uptime=0.60,
        source="reviewed raid policy",
        bar="front",
    )


def _workload_policy(**overrides):
    values = dict(
        requirement_id="major_slayer_provider",
        encounter_id="lokke_hm",
        effect_duration_seconds=10.0,
        required_recipients=12,
        targets_per_application=6,
        max_applications_per_cycle=1,
        window_start_seconds=0.0,
        window_end_seconds=30.0,
        workload_horizon_seconds=30.0,
        minimum_distinct_sources=1,
        gcd_seconds_per_application=1.0,
        primary_role_displacement_seconds=0.25,
        source="reviewed Lokke support plan",
    )
    values.update(overrides)
    return TeamProviderAssignedWorkloadPolicy(**values)


def _plan(character="Magrat", build="DF Healer", casts=(0.0, 20.0)):
    return RotationPlan(
        character,
        build,
        30.0,
        tuple(
            RotationAction(
                time,
                index,
                RotationActionKind.ULTIMATE,
                "Aggressive Horn",
                "front",
            )
            for index, time in enumerate(casts)
        ),
    )


def test_projects_assigned_provider_and_real_plan_casts_into_workload_request():
    projection = TeamProviderAssignmentWorkloadAdapterService.project(
        assignments=(_assignment(_provider()),),
        effect_policies=(_effect_policy(),),
        workload_policies=(_workload_policy(),),
        rotation_plans=(_plan(),),
    )

    assert projection.rejected == ()
    assert len(projection.alternatives) == 1
    alternative = projection.alternatives[0]
    assert alternative.effect_key == "major_slayer"
    assert alternative.duration_seconds == 30.0
    assert alternative.recipient_coverage_result.covered_recipients == 6
    assert alternative.recipient_coverage_result.uncovered_recipients == 6
    assert alternative.temporal_coverage_result.covered_seconds == 20.0
    assert alternative.temporal_coverage_result.coverage_ratio == 2 / 3
    assert alternative.temporal_coverage_result.target_coverage_ratio == 0.60
    assert alternative.temporal_coverage_result.target_coverage_met is True
    assert len(alternative.action_bindings) == 1
    binding = alternative.action_bindings[0]
    assert binding.character_name == "Magrat"
    assert binding.build_name == "DF Healer"
    assert binding.action_name == "Aggressive Horn"
    assert binding.primary_role_displacement_seconds == 0.25
    assert binding.bar == "front"


def test_unresolved_phase11_assignment_fails_closed_instead_of_choosing_backup():
    provider = _provider()
    projection = TeamProviderAssignmentWorkloadAdapterService.project(
        assignments=(
            _assignment(
                provider,
                status=ProviderAssignmentStatus.UNRESOLVED_SELECTION,
            ),
        ),
        effect_policies=(_effect_policy(),),
        workload_policies=(_workload_policy(),),
        rotation_plans=(_plan(),),
    )

    assert projection.alternatives == ()
    assert len(projection.rejected) == 1
    assert "unresolved_selection, not assigned" in projection.rejected[0].blockers[0]


def test_missing_exact_saved_rotation_is_reported_as_candidate_blocker():
    projection = TeamProviderAssignmentWorkloadAdapterService.project(
        assignments=(_assignment(_provider()),),
        effect_policies=(_effect_policy(),),
        workload_policies=(_workload_policy(),),
        rotation_plans=(),
    )

    assert projection.alternatives == ()
    assert projection.rejected[0].blockers == (
        "Magrat / DF Healer: no exact rotation plan is attached",
    )


def test_two_explicit_primary_providers_can_satisfy_distinct_source_and_recipient_policy():
    magrat = _provider()
    rylo = _provider(member_id="rylo", character="Rylonia", build="Support DD")
    projection = TeamProviderAssignmentWorkloadAdapterService.project(
        assignments=(_assignment(magrat, rylo),),
        effect_policies=(_effect_policy(),),
        workload_policies=(
            _workload_policy(
                minimum_distinct_sources=2,
                window_end_seconds=20.0,
                workload_horizon_seconds=20.0,
            ),
        ),
        rotation_plans=(
            RotationPlan(
                "Magrat",
                "DF Healer",
                20.0,
                (RotationAction(0.0, 0, RotationActionKind.ULTIMATE, "Aggressive Horn", "front"),),
            ),
            RotationPlan(
                "Rylonia",
                "Support DD",
                20.0,
                (RotationAction(10.0, 0, RotationActionKind.ULTIMATE, "Aggressive Horn", "front"),),
            ),
        ),
    )

    assert projection.rejected == ()
    alternative = projection.alternatives[0]
    assert alternative.recipient_coverage_result.covered_recipients == 12
    assert alternative.temporal_coverage_result.coverage_ratio == 1.0
    assert alternative.temporal_coverage_result.distinct_source_count == 2
    assert alternative.temporal_coverage_result.distinct_source_requirement_met is True
