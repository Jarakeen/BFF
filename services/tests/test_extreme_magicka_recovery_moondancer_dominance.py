import pytest

from tools.audit_extreme_magicka_recovery_moondancer_dominance import final_upper


def test_final_upper_composes_structural_and_special_before_multiplier():
    result = final_upper(
        shared_flat=3702.294,
        structural=816.0,
        special=474.0,
    )

    assert result == pytest.approx((3702.294 + 816.0 + 474.0) * 1.81)


def test_small_physical_tightening_is_enough_to_lose_to_willow():
    willow = 9259.238
    # The loose capacity screen used 945 + 474 = 1419 pre-percent.  Any legal
    # physical structure below the Willow tie threshold must lose even when the
    # complete Moondancer conditional ceiling is granted.
    result = final_upper(
        shared_flat=3702.294,
        structural=900.0,
        special=474.0,
    )

    assert result < willow


def test_loose_capacity_value_still_survives_as_expected_control():
    willow = 9259.238
    result = final_upper(
        shared_flat=3702.294,
        structural=945.0,
        special=474.0,
    )

    assert result > willow
