from __future__ import annotations

import pytest

from minmax.resource_cost_formula_candidates import (
    evaluate_cost_formula_candidates,
    matching_candidates,
)


def test_flat_then_percent_differs_from_percent_then_flat() -> None:
    candidates = evaluate_cost_formula_candidates(
        base_cost=4050,
        flat_reduction=133,
        percent_reduction=0.07,
    )

    by_name = {candidate.name: candidate for candidate in candidates}
    assert by_name["flat_then_percent_then_increase"].raw_value == pytest.approx(3642.81)
    assert by_name["percent_then_flat_then_increase"].raw_value == pytest.approx(3633.5)


def test_rounding_candidates_are_exposed() -> None:
    candidates = evaluate_cost_formula_candidates(
        base_cost=4050,
        flat_reduction=133,
        percent_reduction=0.07,
    )
    first = candidates[0]
    assert (first.floor, first.nearest_half_up, first.ceiling) == (3642, 3643, 3643)


def test_matching_candidates_reports_exact_formula_and_rounding_pairs() -> None:
    candidates = evaluate_cost_formula_candidates(
        base_cost=4050,
        flat_reduction=133,
        percent_reduction=0.07,
    )
    matches = matching_candidates(candidates, 3643)
    assert ("flat_then_percent_then_increase", "nearest_half_up") in matches
    assert ("flat_then_percent_then_increase", "ceiling") in matches
    assert all(name != "percent_then_flat_then_increase" for name, _ in matches)


def test_invalid_percent_reduction_is_rejected() -> None:
    with pytest.raises(ValueError):
        evaluate_cost_formula_candidates(base_cost=1000, percent_reduction=1.1)
