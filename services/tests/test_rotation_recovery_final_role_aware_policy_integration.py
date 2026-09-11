from types import SimpleNamespace

import pytest

from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_gameplay_policy_assessment_service import (
    RotationGameplayPolicyAssessment,
    RotationGameplayPolicyStatus,
)
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)
from services.rotation_recovery_heavy_final_family_evaluation_service import (
    RotationRecoveryHeavyFinalFamilyEvaluationService,
)
from services.rotation_role_aware_ranking_service import RotationRoleAwareRankingInput


def _scorecard() -> RotationCandidateScorecard:
    return RotationCandidateScorecard(
        consequence=RotationPlanConsequence(
            resource_kind=RotationResourceConsequenceKind.NEUTRAL,
            cast_deltas=(),
            cost_deltas=(),
            total_cost_delta=0,
            minimum_resource_delta=0,
            ending_resource_delta=0,
            shortfall_delta=0,
            wait_delta=0,
        ),
        demand_coverage=(),
        missing_required_effects=(),
        candidate_shortfall=0,
        inherited_unresolved=(),
        candidate_specific_unresolved=(),
    )


def _assessment(candidate_id: str, status: RotationGameplayPolicyStatus):
    return RotationGameplayPolicyAssessment(
        candidate_id=candidate_id,
        policy_id="dd_redundant_personal_heal",
        status=status,
        subject="personal_heal_skill_slot",
        confidence="strong_practice",
        reasons=(f"policy status: {status.value}",),
    )


def _input(
    candidate_id: str,
    *,
    damage: float,
    status: RotationGameplayPolicyStatus,
) -> RotationRoleAwareRankingInput:
    return RotationRoleAwareRankingInput(
        candidate_id=candidate_id,
        scorecard=_scorecard(),
        role_key="dd",
        role_output_value=damage,
        role_output_label="effective damage",
        assigned_support_value=0.0,
        assigned_support_label="assigned support coverage",
        sustain_margin=5000.0,
        primary_role_displacement_seconds=0.0,
        gameplay_policy_assessment=_assessment(candidate_id, status),
    )


def test_final_recovery_family_uses_role_aware_policy_before_dd_damage() -> None:
    snapshots = (
        SimpleNamespace(candidate_id="redundant-heal"),
        SimpleNamespace(candidate_id="clean"),
    )
    by_id = {
        "redundant-heal": _input(
            "redundant-heal",
            damage=200_000.0,
            status=RotationGameplayPolicyStatus.DISFAVORED,
        ),
        "clean": _input(
            "clean",
            damage=100_000.0,
            status=RotationGameplayPolicyStatus.SATISFIED,
        ),
    }

    ranked = RotationRecoveryHeavyFinalFamilyEvaluationService().evaluate_role_aware(
        snapshots,
        input_resolver=lambda snapshot: by_id[snapshot.candidate_id],
    )

    assert [item.candidate_id for item in ranked] == ["clean", "redundant-heal"]
    assert all(item.tier.value == "eligible" for item in ranked)
    assert ranked[0].rank == 1
    assert "gameplay policy dd_redundant_personal_heal: satisfied" in ranked[0].reasons
    assert "gameplay policy dd_redundant_personal_heal: disfavored" in ranked[1].reasons


def test_unresolved_final_policy_evidence_fails_closed() -> None:
    snapshots = (SimpleNamespace(candidate_id="unknown-policy"),)

    ranked = RotationRecoveryHeavyFinalFamilyEvaluationService().evaluate_role_aware(
        snapshots,
        input_resolver=lambda snapshot: _input(
            snapshot.candidate_id,
            damage=250_000.0,
            status=RotationGameplayPolicyStatus.UNRESOLVED,
        ),
    )

    assert len(ranked) == 1
    assert ranked[0].tier.value == "ineligible"
    assert "gameplay policy dd_redundant_personal_heal: unresolved" in ranked[0].reasons


def test_final_role_aware_resolver_rejects_candidate_identity_mismatch() -> None:
    snapshots = (SimpleNamespace(candidate_id="expected"),)

    with pytest.raises(ValueError, match="candidate mismatch"):
        RotationRecoveryHeavyFinalFamilyEvaluationService().evaluate_role_aware(
            snapshots,
            input_resolver=lambda _snapshot: _input(
                "different",
                damage=100_000.0,
                status=RotationGameplayPolicyStatus.SATISFIED,
            ),
        )
