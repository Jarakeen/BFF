from __future__ import annotations

import pytest

from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSExactLeafEvaluation,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSGeneratedFrontierWiringService,
    ExtremeSustainedDPSIndexedFrontierAxis,
)
from services.extreme_sustained_dps_partial_branch_upper_bound_service import (
    ExtremeSustainedDPSBoundEnvelopeInput,
)
from services.extreme_sustained_dps_pruning_service import (
    ExtremeSustainedDPSBoundEvidence,
)


def _bound(value: float | None, *, safe: bool = True, unresolved=()):
    return (
        ExtremeSustainedDPSBoundEnvelopeInput(
            "test ceiling",
            ExtremeSustainedDPSBoundEvidence(
                candidate_key="local",
                upper_bound_dps=value,
                proven_safe=safe,
                source="test",
                unresolved=tuple(unresolved),
            ),
        ),
    )


def _evaluate(node):
    score = float(node.state["score"])
    return ExtremeSustainedDPSExactLeafEvaluation(
        candidate_key=node.candidate_key,
        modeled_dps=score,
        duration_seconds=10.0,
        mechanic_complete=True,
    )


def test_wires_indexed_axes_lazily_into_branch_and_bound() -> None:
    materialized = []

    def first_at(state, index):
        materialized.append(("first", index))
        return {**state, "first": index}

    def second_at(state, index):
        materialized.append(("second", state["first"], index))
        return {**state, "second": index, "score": state["first"] * 10 + index}

    axes = (
        ExtremeSustainedDPSIndexedFrontierAxis(
            "First Axis",
            candidate_count=lambda _state: 2,
            candidate_at=first_at,
        ),
        ExtremeSustainedDPSIndexedFrontierAxis(
            "Second Axis",
            candidate_count=lambda state: state["first"] + 1,
            candidate_at=second_at,
        ),
    )

    result = ExtremeSustainedDPSGeneratedFrontierWiringService.search(
        {},
        axes=axes,
        evaluate_leaf=_evaluate,
        required_duration_seconds=10.0,
    )

    assert result.global_maximum_proven is True
    assert result.best_modeled_dps == 11.0
    assert result.evaluated_leaf_count == 3
    assert materialized == [
        ("first", 0),
        ("first", 1),
        ("second", 0, 0),
        ("second", 1, 0),
        ("second", 1, 1),
    ]


def test_inherited_safe_bound_can_prune_a_child_without_materializing_later_axes() -> None:
    evaluated = []

    def evaluate(node):
        evaluated.append(node.state["choice"])
        return ExtremeSustainedDPSExactLeafEvaluation(
            candidate_key=node.candidate_key,
            modeled_dps=float(node.state["score"]),
            duration_seconds=10.0,
            mechanic_complete=True,
        )

    axis = ExtremeSustainedDPSIndexedFrontierAxis(
        "Choice",
        candidate_count=lambda _state: 2,
        candidate_at=lambda _state, index: {
            "choice": index,
            "score": 100.0 if index == 0 else 40.0,
        },
        bound_inputs=lambda state: _bound(100.0 if state["choice"] == 0 else 50.0),
    )

    result = ExtremeSustainedDPSGeneratedFrontierWiringService.search(
        {},
        axes=(axis,),
        evaluate_leaf=evaluate,
        required_duration_seconds=10.0,
        root_bound_inputs=lambda _state: _bound(100.0),
    )

    assert evaluated == [0]
    assert result.pruned_branch_count == 1
    assert result.best_modeled_dps == 100.0
    assert result.global_maximum_proven is True


def test_missing_bounds_force_exact_work_but_do_not_block_completed_proof() -> None:
    axis = ExtremeSustainedDPSIndexedFrontierAxis(
        "Open",
        candidate_count=lambda _state: 2,
        candidate_at=lambda _state, index: {"score": float(index + 1)},
        bound_inputs=lambda _state: _bound(
            None,
            safe=False,
            unresolved=("no pruning shortcut",),
        ),
    )

    result = ExtremeSustainedDPSGeneratedFrontierWiringService.search(
        {},
        axes=(axis,),
        evaluate_leaf=_evaluate,
        required_duration_seconds=10.0,
    )

    assert result.forced_open_branch_count == 3
    assert result.evaluated_leaf_count == 2
    assert result.best_modeled_dps == 2.0
    assert result.global_maximum_proven is True


def test_empty_dynamic_axis_is_blocking_denominator_evidence() -> None:
    axis = ExtremeSustainedDPSIndexedFrontierAxis(
        "Empty",
        candidate_count=lambda _state: 0,
        candidate_at=lambda _state, _index: None,
    )

    result = ExtremeSustainedDPSGeneratedFrontierWiringService.search(
        {},
        axes=(axis,),
        evaluate_leaf=_evaluate,
        required_duration_seconds=10.0,
    )

    assert result.evaluated_leaf_count == 0
    assert result.global_maximum_proven is False
    assert any("expanded to no children" in row for row in result.unresolved)


def test_duplicate_normalized_axis_names_are_rejected() -> None:
    axis = lambda name: ExtremeSustainedDPSIndexedFrontierAxis(
        name,
        candidate_count=lambda _state: 1,
        candidate_at=lambda state, _index: state,
    )

    with pytest.raises(ValueError, match="duplicate generated"):
        ExtremeSustainedDPSGeneratedFrontierWiringService.search(
            {},
            axes=(axis("Skill Bar"), axis("skill-bar")),
            evaluate_leaf=_evaluate,
            required_duration_seconds=10.0,
        )
