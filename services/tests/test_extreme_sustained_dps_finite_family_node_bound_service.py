from __future__ import annotations

from dataclasses import dataclass, replace
from types import SimpleNamespace

from services.extreme_sustained_dps_finite_family_branch_bound_adapter_service import (
    ExtremeSustainedDPSFiniteFamilyBranchScopeProof,
)
from services.extreme_sustained_dps_finite_family_node_bound_service import (
    ExtremeSustainedDPSFiniteFamilyNodeBoundService,
)
from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSExactLeafEvaluation,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSGeneratedFrontierNode,
    ExtremeSustainedDPSGeneratedFrontierWiringService,
    ExtremeSustainedDPSIndexedFrontierAxis,
)
from services.extreme_sustained_dps_pruning_service import (
    ExtremeSustainedDPSBoundEvidence,
)


def _family_result():
    return SimpleNamespace(
        candidate_key="family:reviewed",
        omitted_scope=(),
        bound=ExtremeSustainedDPSBoundEvidence(
            candidate_key="family:reviewed",
            upper_bound_dps=120.0,
            proven_safe=True,
            source="closed reviewed family",
            unresolved=(),
        ),
    )


def test_node_bound_rejects_scope_for_another_generated_branch() -> None:
    node = ExtremeSustainedDPSGeneratedFrontierNode(
        candidate_key="root|choice:0",
        state=object(),
        coordinates=(("Choice", 0),),
    )

    row = ExtremeSustainedDPSFiniteFamilyNodeBoundService.envelope_input(
        node,
        _family_result(),
        scope=ExtremeSustainedDPSFiniteFamilyBranchScopeProof(
            branch_candidate_key="root|choice:1",
            family_candidate_key="family:reviewed",
            denominator_matches_branch=True,
        ),
    )

    assert row.evidence.candidate_key == node.candidate_key
    assert row.evidence.proven_safe is False
    assert row.evidence.upper_bound_dps is None
    assert any("does not name this generated branch node" in item for item in row.evidence.unresolved)


@dataclass(frozen=True)
class _State:
    selected: int | None = None


def test_node_bound_prunes_matching_generated_frontier_branch() -> None:
    axis = ExtremeSustainedDPSIndexedFrontierAxis(
        "Choice",
        candidate_count=lambda _state: 2,
        candidate_at=lambda state, index: replace(state, selected=index),
    )
    family = _family_result()
    evaluated: list[int] = []

    def branch_bounds(node):
        if node.depth != 1 or node.coordinates[-1][1] != 0:
            return ()
        return (
            ExtremeSustainedDPSFiniteFamilyNodeBoundService.envelope_input(
                node,
                family,
                scope=ExtremeSustainedDPSFiniteFamilyBranchScopeProof(
                    branch_candidate_key=node.candidate_key,
                    family_candidate_key="family:reviewed",
                    denominator_matches_branch=True,
                    source="choice zero is exactly the reviewed finite family",
                ),
            ),
        )

    def evaluate(node):
        evaluated.append(node.state.selected)
        score = 100.0 if node.state.selected == 0 else 150.0
        return ExtremeSustainedDPSExactLeafEvaluation(
            candidate_key=node.candidate_key,
            modeled_dps=score,
            duration_seconds=20.0,
            mechanic_complete=True,
        )

    result = ExtremeSustainedDPSGeneratedFrontierWiringService.search(
        _State(),
        axes=(axis,),
        evaluate_leaf=evaluate,
        required_duration_seconds=20.0,
        root_key="root",
        branch_bound_inputs=branch_bounds,
    )

    assert result.best_modeled_dps == 150.0
    assert result.evaluated_leaf_count == 1
    assert result.pruned_branch_count == 1
    assert evaluated == [1]
    assert result.global_maximum_proven is True
