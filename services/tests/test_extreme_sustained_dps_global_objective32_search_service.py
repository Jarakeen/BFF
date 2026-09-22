from __future__ import annotations

from types import SimpleNamespace

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    CANONICAL_SUSTAINED_DPS_MUTATION_AXES,
    ExtremeSustainedDPSAxisCoverageProof,
)
from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSGeneratedSearchResult,
)
from services.extreme_sustained_dps_global_objective32_search_service import (
    ExtremeSustainedDPSGlobalObjective32SearchService,
)
from services.extreme_sustained_dps_objective32_search_service import (
    ExtremeSustainedDPSObjective32SearchScopeProof,
)
from services.extreme_sustained_dps_runtime_state_frontier_service import (
    ExtremeSustainedDPSRuntimeStateChoice,
    ExtremeSustainedDPSRuntimeStateFrontierService,
)


def _search_result(*, proven=True):
    return ExtremeSustainedDPSGeneratedSearchResult(
        best_modeled_dps=180.0,
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


class _GlobalSearch:
    def __init__(self, result, *, missing_axes=(), inventory_unresolved=()):
        self.result = result
        self.calls = []
        self.missing_axes = tuple(missing_axes)
        self.inventory_unresolved = tuple(inventory_unresolved)

    def axis_inventory(self, *, runtime_state_frontier=None):
        return SimpleNamespace(
            missing_canonical_axes=self.missing_axes,
            unresolved=self.inventory_unresolved,
            searched_canonical_axes=tuple(
                axis
                for axis in CANONICAL_SUSTAINED_DPS_MUTATION_AXES
                if axis not in set(self.missing_axes)
            ),
        )

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _StructuralFamilies:
    @staticmethod
    def coverage():
        return ExtremeSustainedDPSAxisCoverageProof(
            source="validated structural family denominator",
            dominated_axes=("race", "class_route", "attributes"),
        )


def _remaining_without_runtime():
    return ExtremeSustainedDPSAxisCoverageProof(
        source="all generated non-structural non-runtime axes",
        dominated_axes=tuple(
            axis
            for axis in CANONICAL_SUSTAINED_DPS_MUTATION_AXES
            if axis not in {"race", "class_route", "attributes", "runtime_state"}
        ),
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


def test_global_objective32_closes_when_global_tree_and_all_axes_match() -> None:
    global_search = _GlobalSearch(_search_result())
    service = ExtremeSustainedDPSGlobalObjective32SearchService(
        global_search=global_search,
        structural_families=_StructuralFamilies(),
    )
    runtime = _runtime_frontier()

    result = service.search(
        coverage_proofs=(_remaining_without_runtime(),),
        scope_proof=ExtremeSustainedDPSObjective32SearchScopeProof(
            root_candidate_key="generated-global-root",
            coverage_matches_search_denominator=True,
            source="test global denominator proof",
        ),
        runtime_state_frontier=runtime,
        dual_bar_frontier="gear",
        candidate_id_prefix="objective32",
        required_duration_seconds=20.0,
        potion_cooldown_seconds=45.0,
        starting_ultimate=0.0,
        priorities="priorities",
        snapshot_resolver="resolver",
        target_identity="Boss",
        runtime_snapshot="snapshot",
        target_health=1_000_000,
        target_resistance=18_200.0,
    )

    assert result.best_modeled_dps == 180.0
    assert result.finite_denominator_maximum_proven is True
    assert result.theoretical_maximum_proven is True
    assert result.axis_coverage.missing_axes == ()
    assert global_search.calls[0]["runtime_state_frontier"] is runtime


def test_global_objective32_preserves_runtime_omission() -> None:
    service = ExtremeSustainedDPSGlobalObjective32SearchService(
        global_search=_GlobalSearch(_search_result()),
        structural_families=_StructuralFamilies(),
    )

    result = service.search(
        coverage_proofs=(_remaining_without_runtime(),),
        scope_proof=ExtremeSustainedDPSObjective32SearchScopeProof(
            root_candidate_key="generated-global-root",
            coverage_matches_search_denominator=True,
        ),
        runtime_state_frontier=_runtime_frontier(
            omitted_scope=("encounter-triggered runtime histories remain open",)
        ),
        dual_bar_frontier="gear",
        candidate_id_prefix="objective32",
        required_duration_seconds=20.0,
        potion_cooldown_seconds=45.0,
        starting_ultimate=0.0,
        priorities="priorities",
        snapshot_resolver="resolver",
        target_identity="Boss",
        runtime_snapshot="snapshot",
        target_health=1_000_000,
        target_resistance=18_200.0,
    )

    assert result.finite_denominator_maximum_proven is True
    assert result.theoretical_maximum_proven is False
    assert result.closure.omitted_scope == (
        "encounter-triggered runtime histories remain open",
    )


def test_global_objective32_rejects_mismatched_nonstructural_scope_proof() -> None:
    service = ExtremeSustainedDPSGlobalObjective32SearchService(
        global_search=_GlobalSearch(_search_result()),
        structural_families=_StructuralFamilies(),
    )

    result = service.search(
        coverage_proofs=(_remaining_without_runtime(),),
        scope_proof=ExtremeSustainedDPSObjective32SearchScopeProof(
            root_candidate_key="generated-global-root",
            coverage_matches_search_denominator=False,
        ),
        runtime_state_frontier=_runtime_frontier(),
        dual_bar_frontier="gear",
        candidate_id_prefix="objective32",
        required_duration_seconds=20.0,
        potion_cooldown_seconds=45.0,
        starting_ultimate=0.0,
        priorities="priorities",
        snapshot_resolver="resolver",
        target_identity="Boss",
        runtime_snapshot="snapshot",
        target_health=1_000_000,
        target_resistance=18_200.0,
    )

    assert result.finite_denominator_maximum_proven is True
    assert result.theoretical_maximum_proven is False
    assert any(
        "non-structural axis coverage is not proven to match" in item
        for item in result.closure.omitted_scope
    )



def test_global_objective32_refuses_theory_when_tree_is_missing_axis() -> None:
    service = ExtremeSustainedDPSGlobalObjective32SearchService(
        global_search=_GlobalSearch(
            _search_result(),
            missing_axes=("encounter_policy",),
        ),
        structural_families=_StructuralFamilies(),
    )

    result = service.search(
        coverage_proofs=(_remaining_without_runtime(),),
        scope_proof=ExtremeSustainedDPSObjective32SearchScopeProof(
            root_candidate_key="generated-global-root",
            coverage_matches_search_denominator=True,
        ),
        runtime_state_frontier=_runtime_frontier(),
        dual_bar_frontier="gear",
        candidate_id_prefix="objective32",
        required_duration_seconds=20.0,
        potion_cooldown_seconds=45.0,
        starting_ultimate=0.0,
        priorities="priorities",
        snapshot_resolver="resolver",
        target_identity="Boss",
        runtime_snapshot="snapshot",
        target_health=1_000_000,
        target_resistance=18_200.0,
    )

    assert result.finite_denominator_maximum_proven is True
    assert result.theoretical_maximum_proven is False
    assert result.axis_inventory.missing_canonical_axes == ("encounter_policy",)
    assert any(
        "does not physically enumerate" in item
        for item in result.closure.omitted_scope
    )
