from __future__ import annotations

from types import SimpleNamespace

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    CANONICAL_SUSTAINED_DPS_MUTATION_AXES,
    ExtremeSustainedDPSAxisCoverageProof,
)
from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSGeneratedSearchResult,
)
from services.extreme_sustained_dps_objective32_search_service import (
    ExtremeSustainedDPSObjective32SearchScopeProof,
    ExtremeSustainedDPSObjective32SearchService,
)
from services.extreme_sustained_dps_runtime_state_frontier_service import (
    ExtremeSustainedDPSRuntimeStateChoice,
    ExtremeSustainedDPSRuntimeStateFrontierService,
)


def _search_result(*, proven=True):
    return ExtremeSustainedDPSGeneratedSearchResult(
        best_modeled_dps=170.0,
        best_candidates=(),
        unique_leader=None,
        evaluated_leaves=(),
        visited_branch_count=1,
        expanded_branch_count=0,
        evaluated_leaf_count=1,
        pruned_branch_count=0,
        forced_open_branch_count=0,
        global_maximum_proven=proven,
        unique_leader_proven=False,
        evidence=(),
        unresolved=(),
    )


class _PipelineSearch:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def search(self, root_state, **kwargs):
        self.calls.append((root_state, kwargs))
        return self.result


def _proof_without_runtime():
    return ExtremeSustainedDPSAxisCoverageProof(
        source="all non-runtime objective axes proven for test",
        dominated_axes=tuple(
            axis
            for axis in CANONICAL_SUSTAINED_DPS_MUTATION_AXES
            if axis != "runtime_state"
        ),
    )



def _closed_closure_inventory():
    return SimpleNamespace(
        closure_ready=True,
        source_data_blockers=(),
        math_review_blockers=(),
        mechanics_blockers=(),
        mechanics_advisories=(),
    )

def _runtime_frontier(*, omitted_scope=()):
    return ExtremeSustainedDPSRuntimeStateFrontierService.build(
        (
            ExtremeSustainedDPSRuntimeStateChoice("runtime:a", "snapshot-a"),
            ExtremeSustainedDPSRuntimeStateChoice("runtime:b", "snapshot-b"),
        ),
        denominator_proven=True,
        source="reviewed local runtime family",
        omitted_scope=tuple(omitted_scope),
    )


def test_objective32_wrapper_can_close_theory_only_when_search_and_all_axes_close() -> None:
    pipeline = _PipelineSearch(_search_result())
    service = ExtremeSustainedDPSObjective32SearchService(
        pipeline_search=pipeline
    )
    runtime = _runtime_frontier()

    result = service.search(
        closure_inventory=_closed_closure_inventory(),
        "root",
        coverage_proofs=(_proof_without_runtime(),),
        scope_proof=ExtremeSustainedDPSObjective32SearchScopeProof(
            root_candidate_key="generated-root",
            coverage_matches_search_denominator=True,
            source="test exact search denominator proof",
        ),
        required_duration_seconds=20.0,
        runtime_snapshot="fallback",
        target_health=1_000_000,
        target_resistance=18_200.0,
        runtime_state_frontier=runtime,
    )

    assert result.best_modeled_dps == 170.0
    assert result.finite_denominator_maximum_proven is True
    assert result.theoretical_maximum_proven is True
    assert result.axis_coverage.missing_axes == ()
    assert "runtime_state" in result.axis_coverage.dominated_axes
    assert pipeline.calls[0][1]["runtime_state_frontier"] is runtime


def test_objective32_wrapper_preserves_local_runtime_omission_and_withholds_theory() -> None:
    service = ExtremeSustainedDPSObjective32SearchService(
        pipeline_search=_PipelineSearch(_search_result())
    )

    result = service.search(
        closure_inventory=_closed_closure_inventory(),
        "root",
        coverage_proofs=(_proof_without_runtime(),),
        scope_proof=ExtremeSustainedDPSObjective32SearchScopeProof(
            root_candidate_key="generated-root",
            coverage_matches_search_denominator=True,
            source="test exact search denominator proof",
        ),
        required_duration_seconds=20.0,
        runtime_snapshot="fallback",
        target_health=1_000_000,
        target_resistance=18_200.0,
        runtime_state_frontier=_runtime_frontier(
            omitted_scope=("encounter-triggered runtime histories remain open",)
        ),
    )

    assert result.finite_denominator_maximum_proven is True
    assert result.theoretical_maximum_proven is False
    assert result.closure.omitted_scope == (
        "encounter-triggered runtime histories remain open",
    )


def test_objective32_wrapper_does_not_turn_incomplete_finite_search_into_theory() -> None:
    service = ExtremeSustainedDPSObjective32SearchService(
        pipeline_search=_PipelineSearch(_search_result(proven=False))
    )

    result = service.search(
        closure_inventory=_closed_closure_inventory(),
        "root",
        coverage_proofs=(_proof_without_runtime(),),
        scope_proof=ExtremeSustainedDPSObjective32SearchScopeProof(
            root_candidate_key="generated-root",
            coverage_matches_search_denominator=True,
            source="test exact search denominator proof",
        ),
        required_duration_seconds=20.0,
        runtime_snapshot="fallback",
        target_health=1_000_000,
        target_resistance=18_200.0,
        runtime_state_frontier=_runtime_frontier(),
    )

    assert result.finite_denominator_maximum_proven is False
    assert result.theoretical_maximum_proven is False



def test_objective32_wrapper_rejects_coverage_scope_for_different_search_root() -> None:
    service = ExtremeSustainedDPSObjective32SearchService(
        pipeline_search=_PipelineSearch(_search_result())
    )

    result = service.search(
        closure_inventory=_closed_closure_inventory(),
        "root",
        coverage_proofs=(_proof_without_runtime(),),
        scope_proof=ExtremeSustainedDPSObjective32SearchScopeProof(
            root_candidate_key="some-other-root",
            coverage_matches_search_denominator=True,
            source="mismatched test scope",
        ),
        required_duration_seconds=20.0,
        runtime_snapshot="fallback",
        target_health=1_000_000,
        target_resistance=18_200.0,
        runtime_state_frontier=_runtime_frontier(),
    )

    assert result.finite_denominator_maximum_proven is True
    assert result.theoretical_maximum_proven is False
    assert any(
        "different generated search root" in item
        for item in result.closure.omitted_scope
    )


def test_objective32_wrapper_requires_explicit_denominator_equivalence() -> None:
    service = ExtremeSustainedDPSObjective32SearchService(
        pipeline_search=_PipelineSearch(_search_result())
    )

    result = service.search(
        closure_inventory=_closed_closure_inventory(),
        "root",
        coverage_proofs=(_proof_without_runtime(),),
        scope_proof=ExtremeSustainedDPSObjective32SearchScopeProof(
            root_candidate_key="generated-root",
            coverage_matches_search_denominator=False,
            source="test proof intentionally open",
        ),
        required_duration_seconds=20.0,
        runtime_snapshot="fallback",
        target_health=1_000_000,
        target_resistance=18_200.0,
        runtime_state_frontier=_runtime_frontier(),
    )

    assert result.finite_denominator_maximum_proven is True
    assert result.theoretical_maximum_proven is False
    assert any(
        "not proven to match" in item
        for item in result.closure.omitted_scope
    )


def test_objective32_wrapper_defaults_to_canonical_mechanics_closure_inventory() -> None:
    service = ExtremeSustainedDPSObjective32SearchService(
        pipeline_search=_PipelineSearch(_search_result())
    )

    result = service.search(
        "root",
        coverage_proofs=(_proof_without_runtime(),),
        scope_proof=ExtremeSustainedDPSObjective32SearchScopeProof(
            root_candidate_key="generated-root",
            coverage_matches_search_denominator=True,
            source="test exact search denominator proof",
        ),
        required_duration_seconds=20.0,
        runtime_snapshot="fallback",
        target_health=1_000_000,
        target_resistance=18_200.0,
        runtime_state_frontier=_runtime_frontier(),
    )

    assert result.closure_inventory is not None
    assert result.closure.mechanics_closure_complete is False
    assert result.theoretical_maximum_proven is False
