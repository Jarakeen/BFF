import pytest

from tools.audit_extreme_magicka_recovery_worm_raiment_dominance import final_upper


def test_final_upper_composes_structural_and_special_before_multiplier():
    result = final_upper(
        shared_flat=3702.294,
        structural=821.59,
        special=516.0,
    )

    assert result == pytest.approx((3702.294 + 821.59 + 516.0) * 1.81)


def test_expected_physical_tightening_loses_to_willow():
    willow = 9259.238
    result = final_upper(
        shared_flat=3702.294,
        structural=821.59,
        special=516.0,
    )

    assert result < willow


def test_loose_capacity_value_survives_as_control():
    willow = 9259.238
    result = final_upper(
        shared_flat=3702.294,
        structural=945.0,
        special=516.0,
    )

    assert result > willow
