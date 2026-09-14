import pytest

from tools.audit_extreme_magicka_recovery_willow_rebased_flat_screen import prepercent_threshold


def test_prepercent_threshold_inverts_final_score_composition():
    threshold = prepercent_threshold(
        shared_flat=3702.294,
        incumbent_final=9259.238,
        multiplier=1.81,
    )

    assert threshold == pytest.approx(1413.307104972375)
    assert (3702.294 + threshold) * 1.81 == pytest.approx(9259.238)


def test_willow_threshold_prunes_known_small_flat_upper_bounds():
    threshold = prepercent_threshold(
        shared_flat=3702.294,
        incumbent_final=9259.238,
        multiplier=1.81,
    )

    assert 1351.0 < threshold
    assert 1351.376 < threshold
    assert 1371.0 < threshold
    assert 1419.0 > threshold
