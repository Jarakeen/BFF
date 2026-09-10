from types import SimpleNamespace

import pytest

from minmax.demand_action_claim_duration_scheduler import DemandActionClaim
from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_recovery_heavy_stabilized_candidate_service import (
    RotationRecoveryHeavyStabilizedCandidateService,
)


def _plan(*, heavy_time: float | None) -> RotationPlan:
    actions = ()
    if heavy_time is not None:
        actions = (
            RotationAction(
                time_seconds=heavy_time,
                sequence=0,
                kind=RotationActionKind.HEAVY_ATTACK,
                name="heavy_attack",
                bar="back",
            ),
        )
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=actions,
    )


def _stabilization(*, converged: bool, plan: RotationPlan, reason: str):
    return SimpleNamespace(
        converged=converged,
        plan=plan,
        replay=object(),
        iterations=(object(),),
        termination_reason=reason,
        tracked_hard_obligations_satisfied=True,
    )


def test_converged_fixed_point_becomes_generated_candidate_with_final_plan() -> None:
    stable_plan = _plan(heavy_time=18.0)
    stabilization = _stabilization(
        converged=True,
        plan=stable_plan,
        reason="stable_fixed_point",
    )
    lead = SimpleNamespace()
    claim = SimpleNamespace()

    result = RotationRecoveryHeavyStabilizedCandidateService.from_stabilization(
        candidate_id="stable-heavy",
        stabilization=stabilization,
        refresh_leads=(lead,),
        action_claims=(claim,),
    )

    assert result.recommendable is True
    assert result.stabilization is stabilization
    assert result.candidate is not None
    assert result.candidate.candidate_id == "stable-heavy"
    assert result.candidate.plan is stable_plan
    assert result.candidate.refresh_leads == (lead,)
    assert result.candidate.action_claims == (claim,)


def test_non_converged_iteration_limit_is_not_exposed_as_candidate() -> None:
    stabilization = _stabilization(
        converged=False,
        plan=_plan(heavy_time=57.0),
        reason="iteration_limit_reached",
    )

    result = RotationRecoveryHeavyStabilizedCandidateService.from_stabilization(
        candidate_id="unstable-heavy",
        stabilization=stabilization,
    )

    assert result.recommendable is False
    assert result.candidate is None
    assert result.stabilization.termination_reason == "iteration_limit_reached"


def test_converged_but_hard_invalid_plan_still_flows_to_existing_hard_gates() -> None:
    stable_plan = _plan(heavy_time=33.0)
    stabilization = SimpleNamespace(
        converged=True,
        plan=stable_plan,
        replay=object(),
        iterations=(object(),),
        termination_reason="stable_no_legal_improvement",
        tracked_hard_obligations_satisfied=False,
    )

    result = RotationRecoveryHeavyStabilizedCandidateService.from_stabilization(
        candidate_id="stable-but-invalid",
        stabilization=stabilization,
    )

    assert result.recommendable is True
    assert result.candidate is not None
    assert result.candidate.plan is stable_plan
    assert result.stabilization.tracked_hard_obligations_satisfied is False


def test_candidate_id_is_required() -> None:
    stabilization = _stabilization(
        converged=True,
        plan=_plan(heavy_time=None),
        reason="stable_fixed_point",
    )

    with pytest.raises(ValueError, match="candidate_id is required"):
        RotationRecoveryHeavyStabilizedCandidateService.from_stabilization(
            candidate_id="   ",
            stabilization=stabilization,
        )
