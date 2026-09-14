import pytest

from tools.audit_extreme_magicka_recovery_telvanni_enforcer_dominance import final_upper


def test_final_upper_composes_structural_and_exact_special_before_multiplier():
    result = final_upper(shared_flat=3702.294, structural=821.59, special=369.0)

    assert result == pytest.approx((3702.294 + 821.59 + 369.0) * 1.81)


def test_exact_telvanni_branch_loses_to_willow():
    willow = 9259.238
    result = final_upper(shared_flat=3702.294, structural=821.59, special=369.0)

    assert result < willow


def test_generic_double_count_survives_as_expected_control():
    willow = 9259.238
    result = final_upper(shared_flat=3702.294, structural=821.59, special=738.0)

    assert result > willow
