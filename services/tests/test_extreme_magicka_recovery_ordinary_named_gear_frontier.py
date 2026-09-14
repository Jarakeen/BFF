from types import SimpleNamespace

import pytest

from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import (
    PairScore,
    realization_pair_totals,
)


def test_ordinary_max_magicka_conversion_uses_one_weight_undaunted_multiplier():
    conversion = 0.005 * 1.02
    assert conversion == pytest.approx(0.0051)
    assert 1000.0 * conversion == pytest.approx(5.1)


def test_remaining_enlivening_headroom_from_locked_same_build_witness():
    base_enlivening = 26924.736 * 0.005
    assert base_enlivening == pytest.approx(134.62368)
    assert 150.0 - base_enlivening == pytest.approx(15.37632)


def test_realization_pair_totals_compose_distinct_named_set_breakpoints():
    realization = SimpleNamespace(set_ids=(10, 20), counts=(5, 2))
    scores = {
        (10, 5): PairScore(200.0, 1000.0, 205.1, True),
        (20, 2): PairScore(50.0, 500.0, 52.55, True),
    }

    direct, max_magicka = realization_pair_totals(realization, scores)

    assert direct == pytest.approx(250.0)
    assert max_magicka == pytest.approx(1500.0)
