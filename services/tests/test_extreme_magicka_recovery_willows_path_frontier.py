from types import SimpleNamespace

import pytest

from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import PairScore
from tools.audit_extreme_magicka_recovery_willows_path_frontier import (
    best_distinct_capacity_selection,
    companion_pair_totals,
    compose_final,
)


def _score(value: float, *, ordinary: bool = True, max_magicka: float = 0.0) -> PairScore:
    return PairScore(
        direct_recovery=float(value),
        max_magicka_flat=float(max_magicka),
        optimistic_effective_recovery=float(value),
        ordinary=ordinary,
    )


def test_capacity_selection_uses_distinct_set_identities():
    scores = {
        (1, 3): _score(400.0),
        (1, 1): _score(300.0),
        (2, 3): _score(350.0),
        (3, 1): _score(100.0),
    }

    result = best_distinct_capacity_selection(
        challenger_set_id=99,
        pair_scores=scores,
        capacity=7,
    )

    assert result.optimistic_score == pytest.approx(850.0)
    assert set(result.pairs) == {(1, 3), (2, 3), (3, 1)}


def test_capacity_selection_excludes_challenger_identity_and_nonordinary_rows():
    scores = {
        (99, 3): _score(9999.0),
        (1, 3): _score(300.0),
        (2, 3): _score(500.0, ordinary=False),
        (3, 1): _score(100.0),
    }

    result = best_distinct_capacity_selection(
        challenger_set_id=99,
        pair_scores=scores,
        capacity=7,
    )

    assert result.optimistic_score == pytest.approx(400.0)
    assert set(result.pairs) == {(1, 3), (3, 1)}


def test_companion_pair_totals_excludes_willow_and_nonordinary_rows():
    realization = SimpleNamespace(
        set_ids=(99, 1, 2),
        counts=(5, 3, 1),
    )
    scores = {
        (99, 5): _score(129.0, ordinary=False),
        (1, 3): _score(300.0, max_magicka=1000.0),
        (2, 1): _score(500.0, ordinary=False, max_magicka=9999.0),
    }

    recovery, max_magicka = companion_pair_totals(
        realization,
        scores,
        excluded_set_id=99,
    )

    assert recovery == pytest.approx(300.0)
    assert max_magicka == pytest.approx(1000.0)


def test_percent_branch_composes_at_multiplier_layer():
    ordinary = compose_final(shared_flat=3000.0, gear_flat=1000.0, multiplier=1.81)
    willow = compose_final(shared_flat=3000.0, gear_flat=900.0, multiplier=1.99)

    assert ordinary == pytest.approx(7240.0)
    assert willow == pytest.approx(7761.0)
    assert willow > ordinary
