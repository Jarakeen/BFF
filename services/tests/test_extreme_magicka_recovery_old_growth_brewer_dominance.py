import pytest

from tools.audit_extreme_magicka_recovery_old_growth_brewer_dominance import final_upper


def test_final_upper_composes_structural_and_special_before_multiplier():
    result = final_upper(
        shared_flat=3702.294,
        structural=816.0,
        special=503.0,
    )

    assert result == pytest.approx((3702.294 + 816.0 + 503.0) * 1.81)


def test_physical_five_piece_structure_below_willow_threshold_loses():
    willow = 9259.238
    result = final_upper(
        shared_flat=3702.294,
        structural=821.59,
        special=503.0,
    )

    assert result < willow


def test_loose_capacity_value_survives_as_expected_control():
    willow = 9259.238
    result = final_upper(
        shared_flat=3702.294,
        structural=945.0,
        special=503.0,
    )

    assert result > willow
