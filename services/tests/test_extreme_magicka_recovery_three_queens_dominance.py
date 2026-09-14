from types import SimpleNamespace

import pytest

from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import PairScore
from tools.audit_extreme_magicka_recovery_three_queens_dominance import (
    distinct_set_formula_capacity_upper_bound,
    three_queens_optimistic_total,
)


def _pair(*, recovery: float = 0.0, magicka: float = 0.0, ordinary: bool = True) -> PairScore:
    return PairScore(
        direct_recovery=float(recovery),
        max_magicka_flat=float(magicka),
        optimistic_effective_recovery=float(recovery),
        ordinary=ordinary,
    )


def test_formula_capacity_bound_values_max_magicka_at_combined_formula_and_enlivening_rate():
    scores = {
        (1, 3): _pair(recovery=300.0),
        (2, 3): _pair(magicka=10000.0),
        (3, 1): _pair(recovery=100.0),
        (99, 1): _pair(recovery=9999.0),
    }

    upper = distinct_set_formula_capacity_upper_bound(
        challenger_set_id=99,
        challenger_piece_count=5,
        pair_scores=scores,
        max_magicka_to_recovery=0.0153,
    )

    # Seven units remain. Best distinct packing is 3pc direct + 3pc Max Magicka + 1pc direct.
    assert upper == pytest.approx(553.0)


def test_formula_capacity_bound_excludes_nonordinary_pairs():
    scores = {
        (1, 5): _pair(recovery=1000.0, ordinary=False),
        (2, 3): _pair(recovery=300.0),
        (3, 1): _pair(recovery=100.0),
    }

    upper = distinct_set_formula_capacity_upper_bound(
        challenger_set_id=99,
        challenger_piece_count=5,
        pair_scores=scores,
        max_magicka_to_recovery=0.0153,
    )

    assert upper == pytest.approx(400.0)


def test_three_queens_total_overstates_enlivening_by_leaving_it_uncapped():
    baseline, own, total = three_queens_optimistic_total(
        base_max_magicka=26924.736,
        own_raw_max_magicka=3288.0,
        formula_numerator=1.0,
        formula_denominator=100.0,
        resource_multiplier=1.02,
        ordinary_capacity_upper=900.0,
    )

    assert baseline == pytest.approx(269.24736)
    assert own == pytest.approx(50.3064)
    assert total == pytest.approx(1219.55376)


def test_three_queens_total_is_monotone_in_remaining_ordinary_capacity():
    _, _, low = three_queens_optimistic_total(
        base_max_magicka=26924.736,
        own_raw_max_magicka=3288.0,
        formula_numerator=1.0,
        formula_denominator=100.0,
        resource_multiplier=1.02,
        ordinary_capacity_upper=800.0,
    )
    _, _, high = three_queens_optimistic_total(
        base_max_magicka=26924.736,
        own_raw_max_magicka=3288.0,
        formula_numerator=1.0,
        formula_denominator=100.0,
        resource_multiplier=1.02,
        ordinary_capacity_upper=900.0,
    )

    assert high - low == pytest.approx(100.0)
