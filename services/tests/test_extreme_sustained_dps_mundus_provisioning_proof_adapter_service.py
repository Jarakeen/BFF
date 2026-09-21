from __future__ import annotations

from services.extreme_sustained_dps_action_upper_bound_service import (
    ExtremeSustainedDPSActionDominanceProof,
)
from services.extreme_sustained_dps_mundus_provisioning_dominance_service import (
    ExtremeSustainedDPSMundusProvisioningDominanceResult,
)
from services.extreme_sustained_dps_mundus_provisioning_proof_adapter_service import (
    ExtremeSustainedDPSMundusProvisioningProofAdapterService,
)


def _result(*, complete=True):
    unresolved = () if complete else ("one pair unresolved",)
    dominance = ExtremeSustainedDPSActionDominanceProof(
        candidate_key="candidate",
        dominated_axes=("Mundus", "mapped food/drink") if complete else (),
        required_axes=("Mundus", "mapped food/drink"),
        optimistic_upper_damage=150.0 if complete else None,
        source="joint grid",
        unresolved=unresolved,
    )
    return ExtremeSustainedDPSMundusProvisioningDominanceResult(
        candidate_key="candidate",
        expected_combinations=6,
        evaluated_combinations=6,
        resolved_combinations=6 if complete else 5,
        winning_mundus="The Thief" if complete else None,
        winning_food="Food X" if complete else None,
        upper_bound_damage=150.0 if complete else None,
        dominance=dominance,
        evidence=(),
        unresolved=unresolved,
    )


def test_complete_joint_dominance_promotes_both_canonical_axes_and_action_ceiling() -> None:
    result = ExtremeSustainedDPSMundusProvisioningProofAdapterService.adapt(
        _result(complete=True)
    )

    assert result.axis_coverage.dominated_axes == ("mundus", "food")
    assert result.axis_coverage.unresolved == ()
    assert result.action_ceiling.complete is True
    assert result.action_ceiling.upper_bound_damage == 150.0


def test_incomplete_joint_grid_promotes_neither_axis_nor_numeric_ceiling() -> None:
    result = ExtremeSustainedDPSMundusProvisioningProofAdapterService.adapt(
        _result(complete=False)
    )

    assert result.axis_coverage.dominated_axes == ()
    assert result.action_ceiling.complete is False
    assert result.action_ceiling.upper_bound_damage is None
    assert "one pair unresolved" in result.unresolved
