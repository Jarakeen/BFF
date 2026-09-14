import pytest

from services.extreme_percent_vs_flat_dominance_service import (
    ExtremePercentVsFlatDominanceService,
)


def test_percent_branch_is_dominated_below_required_subtotal() -> None:
    row = ExtremePercentVsFlatDominanceService.assess(
        pre_percent_subtotal_upper_bound=8000.0,
        percent_ceiling=18.0,
        displaced_flat_value=1505.0,
    )

    assert row.percent_gain_upper_bound == 1440.0
    assert round(row.required_subtotal_to_match, 6) == round(1505.0 / 0.18, 6)
    assert row.dominated is True


def test_percent_branch_remains_open_when_upper_bound_can_match_flat_value() -> None:
    row = ExtremePercentVsFlatDominanceService.assess(
        pre_percent_subtotal_upper_bound=9000.0,
        percent_ceiling=18.0,
        displaced_flat_value=1505.0,
    )

    assert row.percent_gain_upper_bound == 1620.0
    assert row.dominated is False


def test_invalid_inputs_fail_closed() -> None:
    with pytest.raises(ValueError):
        ExtremePercentVsFlatDominanceService.assess(
            pre_percent_subtotal_upper_bound=-1.0,
            percent_ceiling=18.0,
            displaced_flat_value=1505.0,
        )
    with pytest.raises(ValueError):
        ExtremePercentVsFlatDominanceService.assess(
            pre_percent_subtotal_upper_bound=8000.0,
            percent_ceiling=0.0,
            displaced_flat_value=1505.0,
        )
