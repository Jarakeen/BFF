from __future__ import annotations

import pytest

from minmax.critical_resistance import (
    CRITICAL_RESISTANCE_PER_PERCENT,
    resolve_critical_resistance,
)


def test_cp160_conversion_is_66_rating_per_critical_damage_percent():
    result = resolve_critical_resistance(50.0, 1320.0)

    assert CRITICAL_RESISTANCE_PER_PERCENT == pytest.approx(66.0)
    assert result.reduction_percent == pytest.approx(20.0)
    assert result.effective_critical_damage_percent == pytest.approx(30.0)
    assert result.effective_critical_damage_fraction == pytest.approx(0.30)


def test_critical_resistance_cannot_push_critical_bonus_below_zero():
    result = resolve_critical_resistance(50.0, 6600.0)

    assert result.reduction_percent == pytest.approx(100.0)
    assert result.effective_critical_damage_percent == pytest.approx(0.0)


def test_negative_inputs_are_rejected():
    with pytest.raises(ValueError):
        resolve_critical_resistance(-1.0, 0.0)
    with pytest.raises(ValueError):
        resolve_critical_resistance(50.0, -1.0)
