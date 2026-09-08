from types import SimpleNamespace

from ui.rotation_generation_support import RotationGenerationResult
from ui.rotation_recovery_validation_support import (
    RotationRecoveryValidationScope,
    RotationRecoveryValidationSupport,
)


def _generation_result(stabilization=None):
    return RotationGenerationResult(
        plan=SimpleNamespace(),
        duration_evidence=SimpleNamespace(),
        recovery_stabilization=stabilization,
    )


def test_plain_generation_has_no_recovery_validation() -> None:
    evidence = RotationRecoveryValidationSupport.from_generation_result(
        _generation_result()
    )

    assert evidence.scope is RotationRecoveryValidationScope.NOT_EVALUATED
    assert evidence.canonically_evaluated is False
    assert evidence.selectable is None


def test_resource_fixed_point_does_not_claim_canonical_selectability() -> None:
    evidence = RotationRecoveryValidationSupport.from_generation_result(
        _generation_result(
            SimpleNamespace(
                converged=True,
                termination_reason="stable_fixed_point",
                tracked_hard_obligations_satisfied=True,
            )
        )
    )

    assert evidence.scope is RotationRecoveryValidationScope.RESOURCE_ONLY
    assert evidence.canonically_evaluated is False
    assert evidence.selectable is None
    assert any("resource pressure only" in reason for reason in evidence.reasons)
    assert any("stable_fixed_point" in reason for reason in evidence.reasons)


def test_canonical_pipeline_selected_candidate_is_definitively_selectable() -> None:
    selected = SimpleNamespace(
        candidate_id="validated",
        selectable=True,
        reasons=("all supplied obligations satisfied",),
    )
    result = SimpleNamespace(
        selected_candidate=selected,
        ranked_candidates=(selected,),
    )

    evidence = RotationRecoveryValidationSupport.from_candidate_pipeline_result(result)

    assert evidence.scope is RotationRecoveryValidationScope.CANONICAL_CANDIDATE
    assert evidence.canonically_evaluated is True
    assert evidence.selectable is True
    assert evidence.selected_candidate_id == "validated"
    assert evidence.reasons == ("all supplied obligations satisfied",)


def test_canonical_pipeline_without_winner_is_definitively_nonselectable() -> None:
    rejected = SimpleNamespace(
        candidate_id="rejected",
        selectable=False,
        reasons=("effect uptime below minimum",),
    )
    result = SimpleNamespace(
        selected_candidate=None,
        ranked_candidates=(rejected,),
    )

    evidence = RotationRecoveryValidationSupport.from_candidate_pipeline_result(result)

    assert evidence.scope is RotationRecoveryValidationScope.CANONICAL_CANDIDATE
    assert evidence.canonically_evaluated is True
    assert evidence.selectable is False
    assert evidence.selected_candidate_id is None
    assert evidence.reasons == ("rejected: effect uptime below minimum",)
