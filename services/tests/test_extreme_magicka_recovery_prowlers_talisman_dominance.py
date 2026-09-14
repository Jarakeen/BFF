import pytest

from tools.audit_extreme_magicka_recovery_prowlers_talisman_dominance import final_upper


def test_final_upper_composes_structural_and_special_before_multiplier():
    result = final_upper(
        shared_flat=3702.294,
        structural=1203.0,
        special=175.376,
    )

    assert result == pytest.approx((3702.294 + 1203.0 + 175.376) * 1.81)


def test_prowler_loose_capacity_control_survives_willow():
    willow = 9259.238
    result = final_upper(
        shared_flat=3702.294,
        structural=1332.0,
        special=175.376,
    )

    assert result > willow


def test_physical_tightening_can_close_prowler_even_with_full_enlivening_headroom():
    willow = 9259.238
    result = final_upper(
        shared_flat=3702.294,
        structural=1203.0,
        special=175.376,
    )

    assert result < willow
