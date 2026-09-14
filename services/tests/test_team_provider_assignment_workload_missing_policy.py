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
    TeamProviderAssignmentWorkloadAdapterService,
)


def test_assigned_rotation_effect_without_workload_policy_fails_closed():
    provider = ProviderCandidate(
        requirement_id="major_slayer_provider",
        encounter_id="lokke_hm",
        requirement_type="major_slayer",
        member_id="magrat",
        character_name="Magrat",
        build_name="DF Healer",
        status=ProviderCandidateStatus.VIABLE,
        evidence_sources=("saved build capability",),
    )
    assignment = ProviderAssignment(
        requirement_id="major_slayer_provider",
        encounter_id="lokke_hm",
        requirement_type="major_slayer",
        status=ProviderAssignmentStatus.ASSIGNED,
        primary_providers=(provider,),
        backup_providers=(),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="explicit provider ownership",
    )
    effect_policy = RotationAssignmentEffectPolicy(
        requirement_id="major_slayer_provider",
        encounter_id="lokke_hm",
        requirement_type="major_slayer",
        effect_name="Major Slayer",
        source_skill_name="Aggressive Horn",
        minimum_uptime=0.60,
        source="reviewed raid policy",
        bar="front",
    )

    result = TeamProviderAssignmentWorkloadAdapterService.project(
        assignments=(assignment,),
        effect_policies=(effect_policy,),
        workload_policies=(),
        rotation_plans=(),
    )

    assert result.alternatives == ()
    assert len(result.rejected) == 1
    assert result.rejected[0].effect_key == "major_slayer"
    assert result.rejected[0].blockers == (
        "major_slayer_provider: assigned rotation effect has no explicit provider workload policy",
    )
