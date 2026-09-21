from __future__ import annotations

from types import SimpleNamespace

from services.extreme_sustained_dps_finite_family_branch_bound_adapter_service import (
    ExtremeSustainedDPSFiniteFamilyBranchBoundAdapterService,
    ExtremeSustainedDPSFiniteFamilyBranchScopeProof,
)
from services.extreme_sustained_dps_finite_whole_plan_dominance_service import (
    ExtremeSustainedDPSWholePlanEvaluation,
)
from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSExactLeafEvaluation,
    ExtremeSustainedDPSGeneratedBranchAndBoundSearchService,
    ExtremeSustainedDPSGeneratedSearchBranch,
)
from services.extreme_sustained_dps_pruning_service import (
    ExtremeSustainedDPSBoundEvidence,
)
from services.extreme_sustained_dps_runtime_state_dominance_search_service import (
    ExtremeSustainedDPSRuntimeStateDominanceSearchService,
)
from services.extreme_sustained_dps_runtime_state_frontier_service import (
    ExtremeSustainedDPSRuntimeStateChoice,
    ExtremeSustainedDPSRuntimeStateFrontierService,
)


class _RuntimeEvaluator:
    def evaluate(self, choice):
        scores = {
            "runtime:base": 100.0,
            "runtime:buffed": 120.0,
        }
        return ExtremeSustainedDPSWholePlanEvaluation(
            choice_id=choice.runtime_state_id,
            modeled_dps=scores[choice.runtime_state_id],
            duration_seconds=20.0,
            mechanic_complete=True,
        )


def test_runtime_family_ceiling_prunes_matching_branch_after_higher_incumbent() -> None:
    frontier = ExtremeSustainedDPSRuntimeStateFrontierService.build(
        (
            ExtremeSustainedDPSRuntimeStateChoice("runtime:base", object()),
            ExtremeSustainedDPSRuntimeStateChoice("runtime:buffed", object()),
        ),
        denominator_proven=True,
        source="reviewed complete runtime branch family",
        omitted_scope=("encounter-triggered runtime states belong to other branches",),
    )
    dominance = ExtremeSustainedDPSRuntimeStateDominanceSearchService(
        ".",
        scenario=SimpleNamespace(plan=SimpleNamespace(duration_seconds=20.0)),
        evaluator=_RuntimeEvaluator(),
    ).search(
        candidate_key="family:runtime",
        frontier=frontier,
    )

    adaptation = ExtremeSustainedDPSFiniteFamilyBranchBoundAdapterService.adapt(
        dominance,
        scope=ExtremeSustainedDPSFiniteFamilyBranchScopeProof(
            branch_candidate_key="branch:runtime",
            family_candidate_key="family:runtime",
            denominator_matches_branch=True,
            excluded_omitted_scope=(
                "encounter-triggered runtime states belong to other branches",
            ),
            source="branch partition assigns encounter-triggered states elsewhere",
        ),
    )

    incumbent_leaf = ExtremeSustainedDPSGeneratedSearchBranch(
        candidate_key="leaf:incumbent",
        depth=0,
        is_leaf=True,
        upper_bound=ExtremeSustainedDPSBoundEvidence(
            candidate_key="leaf:incumbent",
            upper_bound_dps=None,
            proven_safe=False,
            source="exact leaf required",
            unresolved=(),
        ),
    )
    runtime_branch = ExtremeSustainedDPSGeneratedSearchBranch(
        candidate_key="branch:runtime",
        depth=0,
        is_leaf=False,
        upper_bound=adaptation.bound,
    )

    expanded = []

    def expand_branch(branch):
        expanded.append(branch.candidate_key)
        raise AssertionError("runtime branch should have been pruned before expansion")

    def evaluate_leaf(branch):
        assert branch.candidate_key == "leaf:incumbent"
        return ExtremeSustainedDPSExactLeafEvaluation(
            candidate_key=branch.candidate_key,
            modeled_dps=150.0,
            duration_seconds=20.0,
            mechanic_complete=True,
        )

    result = ExtremeSustainedDPSGeneratedBranchAndBoundSearchService.search(
        (runtime_branch, incumbent_leaf),
        expand_branch=expand_branch,
        evaluate_leaf=evaluate_leaf,
        required_duration_seconds=20.0,
    )

    assert adaptation.bound.proven_safe is True
    assert adaptation.bound.upper_bound_dps == 120.0
    assert result.best_modeled_dps == 150.0
    assert result.pruned_branch_count == 1
    assert result.expanded_branch_count == 0
    assert expanded == []
    assert result.global_maximum_proven is True
