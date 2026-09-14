import pytest

from tools.audit_extreme_magicka_recovery_shroud_lich_vs_torc import final_score


def test_torc_incumbent_control_matches_verified_score():
    result = final_score(shared_flat=3702.294, structural=1203.0, special=450.0)
    assert result == pytest.approx(9693.08214)


def test_old_loose_shroud_screen_ceiling_still_beats_torc_control():
    torc = final_score(shared_flat=3702.294, structural=1203.0, special=450.0)
    shroud_loose = final_score(shared_flat=3702.294, structural=821.59, special=1622.0)
    assert shroud_loose > torc


def test_shroud_exact_branch_must_clear_required_special_threshold():
    shared = 3702.294
    structural = 821.59
    torc = final_score(shared_flat=shared, structural=1203.0, special=450.0)
    required_special = (torc / 1.81) - shared - structural

    assert required_special == pytest.approx(831.41)
    assert final_score(shared_flat=shared, structural=structural, special=required_special) == pytest.approx(torc)
