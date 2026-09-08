from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryHeavyCandidateOrchestrationInput,
    RotationRecoveryHeavyCandidateOrchestrationService,
)


def _plan(candidate_id: str) -> RotationPlan:
    return RotationPlan(
        character_name="Rotation Test",
        build_name=candidate_id,
        duration_seconds=20.0,
        actions=(),
    )


def _iteration_result(candidate_id: str):
    return SimpleNamespace(candidate_id=candidate_id)


def _family_result(
    candidate_id: str,
    *,
    rank: int,
    tier: RotationCandidateTier = RotationCandidateTier.ELIGIBLE,
    reasons: tuple[str, ...] = (),
):
    return SimpleNamespace(
        candidate_id=candidate_id,
        tier=tier,
        rank=rank,
        reasons=reasons,
    )


class _FakeCandidateStabilizer:
    def stabilize(
        self,
        *,
        build,
        generate,
        evaluate_candidate,
        resource,
        maximum_amount,
        trigger_fraction,
        restoration_resolver,
        reserve_assessment_resolver=None,
        max_iterations=6,
        calculation_context=None,
        maximum_event_resolver=None,
    ):
        plan = generate(None)
        replay = SimpleNamespace(final_plan_id=plan.build_name)
        evaluate_candidate(plan, replay)
        valid = plan.build_name == "legal-lower-soft-rank"
        return SimpleNamespace(
            plan=plan,
            replay=replay,
            converged=True,
            termination_reason=(
                "stable_fixed_point" if valid else "stable_no_legal_improvement"
            ),
            tracked_hard_obligations_satisfied=valid,
        )


def _candidate(candidate_id: str, *, evaluation_id: str | None = None):
    return RecoveryHeavyCandidateOrchestrationInput(
        candidate_id=candidate_id,
        generate=lambda _pressure, value=candidate_id: _plan(value),
        evaluate_candidate=lambda _plan, _replay, value=(evaluation_id or candidate_id): (
            _iteration_result(value)
        ),
    )


def test_orchestration_selects_recovery_valid_candidate_over_better_soft_rank() -> None:
    service = RotationRecoveryHeavyCandidateOrchestrationService(
        stabilization_service=_FakeCandidateStabilizer()
    )
    build = PlayerBuild(Name="Rotation Test", BuildName="Role Neutral")
    observed_family = []

    def evaluate_final_family(snapshots):
        observed_family.extend(snapshots)
        return (
            _family_result(
                "better-soft-rank-but-invalid-recovery",
                rank=1,
                reasons=("better family-level soft rank",),
            ),
            _family_result("legal-lower-soft-rank", rank=2),
        )

    result = service.orchestrate(
        build=build,
        candidates=(
            _candidate("better-soft-rank-but-invalid-recovery"),
            _candidate("legal-lower-soft-rank"),
        ),
        evaluate_final_family=evaluate_final_family,
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.30,
        restoration_resolver=lambda _heavy: None,
    )

    assert [item.candidate_id for item in observed_family] == [
        "better-soft-rank-but-invalid-recovery",
        "legal-lower-soft-rank",
    ]
    assert result.selected_candidate is not None
    assert result.selected_candidate.candidate_id == "legal-lower-soft-rank"
    assert result.selected_candidate.evaluation.rank == 2
    assert result.ranked_candidates[0].candidate_id == "legal-lower-soft-rank"
    assert result.ranked_candidates[0].selectable is True
    assert result.ranked_candidates[1].candidate_id == (
        "better-soft-rank-but-invalid-recovery"
    )
    assert result.ranked_candidates[1].selectable is False


def test_orchestration_rejects_iteration_evaluation_candidate_identity_drift() -> None:
    service = RotationRecoveryHeavyCandidateOrchestrationService(
        stabilization_service=_FakeCandidateStabilizer()
    )

    with pytest.raises(ValueError, match="iteration evaluation candidate_id mismatch"):
        service.orchestrate(
            build=PlayerBuild(Name="Rotation Test", BuildName="Role Neutral"),
            candidates=(
                _candidate(
                    "legal-lower-soft-rank",
                    evaluation_id="different-candidate",
                ),
            ),
            evaluate_final_family=lambda _snapshots: (
                _family_result("legal-lower-soft-rank", rank=1),
            ),
            resource=ResourceType.MAGICKA,
            maximum_amount=30000,
            trigger_fraction=0.30,
            restoration_resolver=lambda _heavy: None,
        )


def test_orchestration_requires_exact_final_family_candidate_set() -> None:
    service = RotationRecoveryHeavyCandidateOrchestrationService(
        stabilization_service=_FakeCandidateStabilizer()
    )

    with pytest.raises(ValueError, match="final recovery family evaluation candidate set mismatch"):
        service.orchestrate(
            build=PlayerBuild(Name="Rotation Test", BuildName="Role Neutral"),
            candidates=(
                _candidate("better-soft-rank-but-invalid-recovery"),
                _candidate("legal-lower-soft-rank"),
            ),
            evaluate_final_family=lambda _snapshots: (
                _family_result("legal-lower-soft-rank", rank=1),
            ),
            resource=ResourceType.MAGICKA,
            maximum_amount=30000,
            trigger_fraction=0.30,
            restoration_resolver=lambda _heavy: None,
        )
