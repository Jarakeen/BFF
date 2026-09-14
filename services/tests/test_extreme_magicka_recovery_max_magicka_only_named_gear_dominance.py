import pytest

from tools.audit_extreme_magicka_recovery_max_magicka_only_named_gear_dominance import dominance_row


def test_dominance_row_rejects_physically_available_challenger_below_incumbent():
    row = dominance_row(
        set_id=1,
        set_name="Fixture",
        piece_count=5,
        structural_score=1200.0,
        enlivening_ceiling=15.376,
        incumbent=1332.0,
    )
    assert row.physically_available
    assert row.optimistic_total == pytest.approx(1215.376)
    assert row.margin == pytest.approx(116.624)
    assert row.dominated


def test_dominance_row_does_not_hide_challenger_at_or_above_incumbent():
    row = dominance_row(
        set_id=2,
        set_name="Fixture",
        piece_count=1,
        structural_score=1320.0,
        enlivening_ceiling=15.376,
        incumbent=1332.0,
    )
    assert row.optimistic_total == pytest.approx(1335.376)
    assert not row.dominated


def test_dominance_row_marks_structurally_impossible_branch_dominated():
    row = dominance_row(
        set_id=3,
        set_name="Fixture",
        piece_count=5,
        structural_score=None,
        enlivening_ceiling=15.376,
        incumbent=1332.0,
    )
    assert not row.physically_available
    assert row.optimistic_total is None
    assert row.margin is None
    assert row.dominated
