from types import SimpleNamespace

import pytest

from tools.audit_extreme_magicka_recovery_armor_mundus_frontier import (
    ArmorMundusComposedCandidate,
    globally_locked_winner,
)


def _row(*, value: float, slope: float, light: int = 7, medium: int = 0, heavy: int = 0):
    source = SimpleNamespace()
    return ArmorMundusComposedCandidate(
        source=source,
        light_pieces=light,
        medium_pieces=medium,
        heavy_pieces=heavy,
        armor_percent=max(0.0, slope - 1.53),
        class_percent=0.53,
        undaunted_percent=0.02,
        same_build_max_magicka=26924.736,
        enlivening=134.62368,
        final_value=value,
        future_additive_slope=slope,
    )


def test_future_additive_lock_accepts_current_winner_with_highest_slope():
    winner = _row(value=6200.0, slope=1.81)
    challenger = _row(value=6100.0, slope=1.77, light=6, medium=1)

    locked, margin = globally_locked_winner((winner, challenger))

    assert locked is True
    assert margin == pytest.approx(100.0)


def test_future_additive_lock_rejects_current_winner_with_lower_slope():
    winner = _row(value=6200.0, slope=1.70)
    challenger = _row(value=6100.0, slope=1.81, light=6, medium=1)

    locked, margin = globally_locked_winner((winner, challenger))

    assert locked is False
    assert margin == pytest.approx(100.0)


def test_weight_type_count_tracks_distinct_equipped_weights():
    row = _row(value=6200.0, slope=1.81, light=5, medium=1, heavy=1)

    assert row.weight_type_count == 3
