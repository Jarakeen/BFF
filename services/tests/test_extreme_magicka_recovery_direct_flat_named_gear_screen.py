from types import SimpleNamespace

import pytest

from tools.audit_extreme_magicka_recovery_direct_flat_named_gear_screen import (
    distinct_set_capacity_upper_bound,
)
from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import PairScore


def _score(value: float, *, ordinary: bool = True) -> PairScore:
    return PairScore(
        direct_recovery=float(value),
        max_magicka_flat=0.0,
        optimistic_effective_recovery=float(value),
        ordinary=ordinary,
    )


def test_capacity_bound_uses_each_set_identity_at_most_once():
    challenger = SimpleNamespace(set_id=99, piece_count=5)
    pair_scores = {
        (1, 3): _score(300.0),
        (1, 1): _score(200.0),
        (2, 3): _score(250.0),
        (3, 1): _score(100.0),
    }

    # Seven units remain. Best legal-with-respect-to-identity abstract packing is
    # set 1 at 3pc + set 2 at 3pc + set 3 at 1pc = 650, not repeated set 1.
    assert distinct_set_capacity_upper_bound(challenger, pair_scores) == pytest.approx(650.0)


def test_capacity_bound_can_leave_units_unused():
    challenger = SimpleNamespace(set_id=99, piece_count=10)
    pair_scores = {
        (1, 3): _score(500.0),
        (2, 1): _score(80.0),
    }

    # Only two units remain, so the 3pc breakpoint cannot fit. One unit may stay unused.
    assert distinct_set_capacity_upper_bound(challenger, pair_scores) == pytest.approx(80.0)


def test_capacity_bound_excludes_challenger_identity_and_nonordinary_pairs():
    challenger = SimpleNamespace(set_id=7, piece_count=5)
    pair_scores = {
        (7, 1): _score(999.0),
        (1, 3): _score(300.0),
        (2, 3): _score(250.0, ordinary=False),
        (3, 1): _score(100.0),
    }

    assert distinct_set_capacity_upper_bound(challenger, pair_scores) == pytest.approx(400.0)


def test_capacity_bound_rejects_impossible_challenger_piece_count():
    challenger = SimpleNamespace(set_id=1, piece_count=13)
    assert distinct_set_capacity_upper_bound(challenger, {}) is None
