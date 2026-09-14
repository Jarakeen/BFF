import pytest

from tools.audit_extreme_magicka_recovery_wrathsun_dominance import final_upper


def test_final_upper_composes_structural_and_special_before_multiplier():
    result = final_upper(
        shared_flat=3702.294,
        structural=816.0,
        special=630.0,
    )

    assert result == pytest.approx((3702.294 + 816.0 + 630.0) * 1.81)


def test_physical_five_piece_structure_can_still_survive_with_full_wrathsun_ceiling():
    willow = 9259.238
    result = final_upper(
        shared_flat=3702.294,
        structural=821.59,
        special=630.0,
    )

    assert result > willow


def test_tighter_special_ceiling_would_be_enough_to_lose():
    willow = 9259.238
    result = final_upper(
        shared_flat=3702.294,
        structural=821.59,
        special=500.0,
    )

    assert result < willow
