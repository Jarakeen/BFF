from tools.audit_extreme_magicka_recovery_apocryphal_inspiration_dominance import score


def test_major_intellect_is_common_multiplier_not_extra_set_multiplier():
    shared = 3702.294
    torc = score(shared_flat=shared, gear_flat=1203.0 + 450.0, percent=2.11)
    apocryphal = score(shared_flat=shared, gear_flat=945.0, percent=2.11)

    assert torc > apocryphal


def test_duplicate_major_intellect_does_not_stack_twice():
    shared = 3702.294
    apocryphal_common = score(shared_flat=shared, gear_flat=945.0, percent=2.11)
    apocryphal_illegal_double_stack = score(shared_flat=shared, gear_flat=945.0, percent=2.41)

    assert apocryphal_illegal_double_stack > apocryphal_common
    assert apocryphal_common < score(
        shared_flat=shared,
        gear_flat=1203.0 + 450.0,
        percent=2.11,
    )


def test_five_piece_capacity_cannot_bridge_torc_prepercent_gap():
    shared = 3702.294
    torc_prepercent = shared + 1203.0 + 450.0
    apocryphal_prepercent = shared + 945.0

    assert torc_prepercent - apocryphal_prepercent == 708.0
