from __future__ import annotations

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    CANONICAL_SUSTAINED_DPS_MUTATION_AXES,
    ExtremeSustainedDPSAxisCoverageProof,
    ExtremeSustainedDPSAxisDominanceCompositionService,
)
from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSExactLeafEvaluation,
    ExtremeSustainedDPSGeneratedSearchResult,
)
from services.extreme_sustained_dps_theoretical_maximum_closure_service import (
    ExtremeSustainedDPSTheoreticalMaximumClosureService,
)


def _search(*, proven=True):
    leaf = ExtremeSustainedDPSExactLeafEvaluation(
        candidate_key="leaf:test",
        modeled_dps=150.0,
        duration_seconds=20.0,
        mechanic_complete=True,
    )
    return ExtremeSustainedDPSGeneratedSearchResult(
        best_modeled_dps=150.0,
        best_candidates=(leaf,),
        unique_leader=leaf if proven else None,
        evaluated_leaves=(leaf,),
        visited_branch_count=1,
        expanded_branch_count=0,
        evaluated_leaf_count=1,
        pruned_branch_count=0,
        forced_open_branch_count=0,
        global_maximum_proven=proven,
        unique_leader_proven=bool(proven),
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



def test_axis_proof_omission_blocks_theoretical_claim_without_manual_scope_argument() -> None:
    proof = ExtremeSustainedDPSAxisCoverageProof(
        source="finite all-axis family with open timing",
        dominated_axes=tuple(CANONICAL_SUSTAINED_DPS_MUTATION_AXES),
        omitted_scope=("continuous potion first-use offset remains open",),
    )
    coverage = ExtremeSustainedDPSAxisDominanceCompositionService.compose(
        "objective:32",
        required_axes=tuple(CANONICAL_SUSTAINED_DPS_MUTATION_AXES),
        proofs=(proof,),
    )

    result = ExtremeSustainedDPSTheoreticalMaximumClosureService.close(
        _search(),
        axis_coverage=coverage,
    )

    assert result.canonical_axis_coverage_complete is True
    assert result.theoretical_maximum_proven is False
    assert result.omitted_scope == (
        "continuous potion first-use offset remains open",
    )


def test_mechanics_closure_inventory_blocks_theoretical_claim() -> None:
    inventory = type(
        "Inventory",
        (),
        {
            "closure_ready": False,
            "source_data_blockers": ("scaled runtime debuff unresolved",),
            "math_review_blockers": (),
            "mechanics_blockers": (),
            "mechanics_advisories": (),
        },
    )()

    result = ExtremeSustainedDPSTheoreticalMaximumClosureService.close(
        _search(),
        axis_coverage=_coverage(),
        closure_inventory=inventory,
    )

    assert result.finite_denominator_maximum_proven is True
    assert result.canonical_axis_coverage_complete is True
    assert result.mechanics_closure_complete is False
    assert result.theoretical_maximum_proven is False
    assert any("mechanics closure remains open" in row for row in result.unresolved)


def test_closed_mechanics_inventory_allows_existing_theoretical_proof() -> None:
    inventory = type(
        "Inventory",
        (),
        {
            "closure_ready": True,
            "source_data_blockers": (),
            "math_review_blockers": (),
            "mechanics_blockers": (),
            "mechanics_advisories": (),
        },
    )()

    result = ExtremeSustainedDPSTheoreticalMaximumClosureService.close(
        _search(),
        axis_coverage=_coverage(),
        closure_inventory=inventory,
    )

    assert result.mechanics_closure_complete is True
    assert result.theoretical_maximum_proven is True


def test_truthy_non_boolean_mechanics_closure_cannot_launder_proof() -> None:
    inventory = type(
        "Inventory",
        (),
        {
            "closure_ready": "false",
            "source_data_blockers": (),
            "math_review_blockers": (),
            "mechanics_blockers": (),
            "mechanics_advisories": (),
        },
    )()

    try:
        ExtremeSustainedDPSTheoreticalMaximumClosureService.close(
            _search(),
            axis_coverage=_coverage(),
            closure_inventory=inventory,
        )
    except TypeError as exc:
        assert "boolean closure_ready" in str(exc)
    else:
        raise AssertionError("truthy non-boolean closure proof must fail closed")


def test_malformed_mechanics_blocker_collection_cannot_launder_proof() -> None:
    inventory = type(
        "Inventory",
        (),
        {
            "closure_ready": True,
            "source_data_blockers": [],
            "math_review_blockers": (),
            "mechanics_blockers": (),
            "mechanics_advisories": (),
        },
    )()

    try:
        ExtremeSustainedDPSTheoreticalMaximumClosureService.close(
            _search(),
            axis_coverage=_coverage(),
            closure_inventory=inventory,
        )
    except TypeError as exc:
        assert "source_data_blockers must be a tuple" in str(exc)
    else:
        raise AssertionError("malformed closure blocker collection must fail closed")


def test_theoretical_closure_rejects_duck_typed_search_result() -> None:
    malformed = type(
        "SearchResult",
        (),
        {"global_maximum_proven": True, "best_modeled_dps": 150.0},
    )()
    try:
        ExtremeSustainedDPSTheoreticalMaximumClosureService.close(
            malformed,  # type: ignore[arg-type]
            axis_coverage=_coverage(),
        )
    except TypeError as exc:
        assert "canonical generated search result" in str(exc)
    else:
        raise AssertionError("duck-typed generated search result must fail closed")


def test_theoretical_closure_rejects_non_tuple_manual_omitted_scope() -> None:
    try:
        ExtremeSustainedDPSTheoreticalMaximumClosureService.close(
            _search(),
            axis_coverage=_coverage(),
            omitted_scope=["open timing"],  # type: ignore[arg-type]
        )
    except TypeError as exc:
        assert "omitted_scope must be a tuple" in str(exc)
    else:
        raise AssertionError("non-tuple omitted scope must fail closed")
