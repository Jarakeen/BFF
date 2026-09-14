import pytest

from tools.audit_extreme_magicka_recovery_torc_tonal_constancy_dominance import final_score


def test_final_score_composes_torc_special_before_multiplier():
    result = final_score(
        shared_flat=3702.294,
        structural=1203.0,
        special=450.0,
    )

    assert result == pytest.approx((3702.294 + 1203.0 + 450.0) * 1.81)


def test_expected_one_mythic_physical_structure_can_beat_willow_with_full_torc_condition():
    willow = 9259.238
    result = final_score(
        shared_flat=3702.294,
        structural=1203.0,
        special=450.0,
    )

    assert result > willow


def test_torc_without_conditional_recovery_does_not_beat_willow():
    willow = 9259.238
    result = final_score(
        shared_flat=3702.294,
        structural=1203.0,
        special=0.0,
    )

    assert result < willow
