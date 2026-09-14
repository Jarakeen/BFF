import pytest

from tools.audit_extreme_magicka_recovery_willow_rebased_flat_screen import (
    canonical_special_triage_pairs,
    prepercent_threshold,
)


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


def test_special_triage_pairs_preserve_only_supplied_special_queue():
    special_queue = (
        (101, "Special A", 5),
        (202, "Special B", 1),
    )

    assert canonical_special_triage_pairs(special_queue) == special_queue


def test_special_triage_pairs_fail_closed_on_noncanonical_shape():
    with pytest.raises(ValueError, match="must have 3 fields"):
        canonical_special_triage_pairs(((101, 5),))
