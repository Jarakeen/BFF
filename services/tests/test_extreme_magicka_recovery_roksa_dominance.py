import pytest

from tools.audit_extreme_magicka_recovery_roksa_dominance import final_upper


def test_final_upper_composes_structural_and_special_before_multiplier():
    result = final_upper(
        shared_flat=3702.294,
        structural=1203.0,
        special=240.0,
    )

    assert result == pytest.approx((3702.294 + 1203.0 + 240.0) * 1.81)


def test_roksa_needs_less_than_loose_structural_bound_to_lose_to_willow():
    willow = 9259.238
    result = final_upper(
        shared_flat=3702.294,
        structural=1160.0,
        special=240.0,
    )

    assert result < willow


def test_loose_capacity_value_still_survives_as_expected_control():
    willow = 9259.238
    result = final_upper(
        shared_flat=3702.294,
        structural=1203.0,
        special=240.0,
    )

    assert result > willow
