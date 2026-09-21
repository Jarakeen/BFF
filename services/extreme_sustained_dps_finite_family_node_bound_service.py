from __future__ import annotations

"""Bind a proven finite-family ceiling to one exact generated frontier node."""

from services.extreme_sustained_dps_finite_family_branch_bound_adapter_service import (
    ExtremeSustainedDPSFiniteFamilyBranchBoundAdapterService,
    ExtremeSustainedDPSFiniteFamilyBranchScopeProof,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSGeneratedFrontierNode,
)
from services.extreme_sustained_dps_partial_branch_upper_bound_service import (
    ExtremeSustainedDPSBoundEnvelopeInput,
)
from services.extreme_sustained_dps_pruning_service import (
    ExtremeSustainedDPSBoundEvidence,
)


class ExtremeSustainedDPSFiniteFamilyNodeBoundService:
    """Produce one fail-closed bound input tied to the generated node identity."""

    @classmethod
    def envelope_input(
        cls,
        node: ExtremeSustainedDPSGeneratedFrontierNode,
        result: object,
        *,
        scope: ExtremeSustainedDPSFiniteFamilyBranchScopeProof,
        label: str = "finite-family whole-plan dominance",
    ) -> ExtremeSustainedDPSBoundEnvelopeInput:
        node_key = str(node.candidate_key or "").strip()
        normalized_label = " ".join(str(label or "").strip().split())
        if not normalized_label:
            normalized_label = "finite-family whole-plan dominance"

        if scope.branch_candidate_key != node_key:
            return ExtremeSustainedDPSBoundEnvelopeInput(
                normalized_label,
                ExtremeSustainedDPSBoundEvidence(
                    candidate_key=node_key,
                    upper_bound_dps=None,
                    proven_safe=False,
                    source="finite-family node-bound adaptation withheld",
                    unresolved=(
                        "Finite-family branch-scope proof does not name this generated branch node",
                    ),
                ),
            )

        adaptation = ExtremeSustainedDPSFiniteFamilyBranchBoundAdapterService.adapt(
            result,
            scope=scope,
        )
        bound = adaptation.bound
        if bound.candidate_key != node_key:
            bound = ExtremeSustainedDPSBoundEvidence(
                candidate_key=node_key,
                upper_bound_dps=None,
                proven_safe=False,
                source="finite-family node-bound adaptation withheld",
                unresolved=(
                    *tuple(bound.unresolved),
                    "Finite-family branch-bound adaptation returned a mismatched generated node identity",
                ),
            )

        return ExtremeSustainedDPSBoundEnvelopeInput(
            normalized_label,
            bound,
        )


__all__ = ["ExtremeSustainedDPSFiniteFamilyNodeBoundService"]
