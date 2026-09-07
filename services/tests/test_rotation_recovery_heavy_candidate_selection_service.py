from types import SimpleNamespace

from services.rotation_candidate_ranking_service import RotationCandidateTier
from services.rotation_recovery_heavy_candidate_selection_service import (
    RecoveryStabilizedCandidateInput,
    RotationRecoveryHeavyCandidateSelectionService,
)


def _evaluation(
    candidate_id: str,
    *,
    tier: RotationCandidateTier = RotationCandidateTier.ELIGIBLE,
    rank: int = 1,
    reasons: tuple[str, ...] = (),
):
    return SimpleNamespace(
        candidate_id=candidate_id,
        tier=tier,
        rank=rank,
        reasons=reasons,
    )


def _stabilization(
    reason: str,
    *,
    converged: bool = True,
    satisfied: bool = True,
):
    return SimpleNamespace(
        converged=converged,
        termination_reason=reason,
        tracked_hard_obligations_satisfied=satisfied,
    )


def test_valid_fixed_point_outranks_better_soft_rank_with_no_legal_improvement() -> None:
    service = RotationRecoveryHeavyCandidateSelectionService()

    ranked = service.rank(
        (
            RecoveryStabilizedCandidateInput(
                evaluation=_evaluation("stable-invalid", rank=1),
                stabilization=_stabilization(
                    "stable_no_legal_improvement",
                    satisfied=False,
                ),
            ),
            RecoveryStabilizedCandidateInput(
                evaluation=_evaluation("stable-valid", rank=2),
                stabilization=_stabilization("stable_fixed_point"),
            ),
        )
    )

    assert [item.candidate_id for item in ranked] == [
        "stable-valid",
        "stable-invalid",
    ]
    assert ranked[0].selectable is True
    assert ranked[1].selectable is False
    assert any("no legal improvement" in reason for reason in ranked[1].reasons)
    assert service.select_best(
        (
            RecoveryStabilizedCandidateInput(
                evaluation=_evaluation("stable-invalid", rank=1),
                stabilization=_stabilization(
                    "stable_no_legal_improvement",
                    satisfied=False,
                ),
            ),
            RecoveryStabilizedCandidateInput(
                evaluation=_evaluation("stable-valid", rank=2),
                stabilization=_stabilization("stable_fixed_point"),
            ),
        )
    ).candidate_id == "stable-valid"


def test_iteration_limit_candidate_is_not_selectable_even_when_evaluation_is_eligible() -> None:
    service = RotationRecoveryHeavyCandidateSelectionService()
    candidates = (
        RecoveryStabilizedCandidateInput(
            evaluation=_evaluation("oscillating", rank=1),
            stabilization=_stabilization(
                "iteration_limit_reached",
                converged=False,
                satisfied=True,
            ),
        ),
    )

    ranked = service.rank(candidates)

    assert ranked[0].selectable is False
    assert any("iteration limit" in reason for reason in ranked[0].reasons)
    assert service.select_best(candidates) is None


def test_canonical_ineligible_candidate_cannot_be_selected_from_valid_fixed_point() -> None:
    service = RotationRecoveryHeavyCandidateSelectionService()
    candidates = (
        RecoveryStabilizedCandidateInput(
            evaluation=_evaluation(
                "mechanic-failure",
                tier=RotationCandidateTier.INELIGIBLE,
                rank=1,
                reasons=("missing explicit demand requirement",),
            ),
            stabilization=_stabilization("stable_fixed_point"),
        ),
    )

    ranked = service.rank(candidates)

    assert ranked[0].selectable is False
    assert ranked[0].reasons == ("missing explicit demand requirement",)
    assert service.select_best(candidates) is None
