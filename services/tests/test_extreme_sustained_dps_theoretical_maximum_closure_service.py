from __future__ import annotations

from dataclasses import replace

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    CANONICAL_SUSTAINED_DPS_MUTATION_AXES,
    ExtremeSustainedDPSAxisCoverageProof,
    ExtremeSustainedDPSAxisDominanceCompositionService,
)
from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSGeneratedSearchResult,
)
from services.extreme_sustained_dps_theoretical_maximum_closure_service import (
    ExtremeSustainedDPSTheoreticalMaximumClosureService,
)


def _search(*, proven=True):
    return ExtremeSustainedDPSGeneratedSearchResult(
        best_modeled_dps=150.0,
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


def _coverage(*, required=None, dominated=None):
    required_axes = tuple(
        CANONICAL_SUSTAINED_DPS_MUTATION_AXES
        if required is None
        else required
    )
    dominated_axes = tuple(
        CANONICAL_SUSTAINED_DPS_MUTATION_AXES
        if dominated is None
        else dominated
    )
    return ExtremeSustainedDPSAxisDominanceCompositionService.compose(
        "objective:32",
        required_axes=required_axes,
        proofs=(
            ExtremeSustainedDPSAxisCoverageProof(
                source="test complete denominator",
                dominated_axes=dominated_axes,
            ),
        ),
    )


def test_closes_theoretical_maximum_only_when_tree_axes_and_scope_all_close() -> None:
    result = ExtremeSustainedDPSTheoreticalMaximumClosureService.close(
        _search(),
        axis_coverage=_coverage(),
    )

    assert result.finite_denominator_maximum_proven is True
    assert result.canonical_axis_coverage_complete is True
    assert result.theoretical_maximum_proven is True
    assert result.best_modeled_dps == 150.0
    assert result.unresolved == ()


def test_finite_tree_maximum_does_not_hide_missing_canonical_axis() -> None:
    required = tuple(
        axis
        for axis in CANONICAL_SUSTAINED_DPS_MUTATION_AXES
        if axis != "runtime_state"
    )
    result = ExtremeSustainedDPSTheoreticalMaximumClosureService.close(
        _search(),
        axis_coverage=_coverage(required=required, dominated=required),
    )

    assert result.finite_denominator_maximum_proven is True
    assert result.canonical_axis_coverage_complete is False
    assert result.theoretical_maximum_proven is False
    assert any("runtime_state" in row for row in result.unresolved)


def test_explicitly_omitted_timing_scope_blocks_theoretical_claim() -> None:
    result = ExtremeSustainedDPSTheoreticalMaximumClosureService.close(
        _search(),
        axis_coverage=_coverage(),
        omitted_scope=("continuous potion first-use offsets remain open",),
    )

    assert result.canonical_axis_coverage_complete is True
    assert result.theoretical_maximum_proven is False
    assert result.omitted_scope == (
        "continuous potion first-use offsets remain open",
    )
    assert any("explicitly omitted" in row for row in result.unresolved)


def test_unproven_finite_search_cannot_close_theoretical_maximum() -> None:
    result = ExtremeSustainedDPSTheoreticalMaximumClosureService.close(
        _search(proven=False),
        axis_coverage=_coverage(),
    )

    assert result.finite_denominator_maximum_proven is False
    assert result.theoretical_maximum_proven is False
    assert any("finite search denominator" in row for row in result.unresolved)
