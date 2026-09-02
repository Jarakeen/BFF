from tools.audit_phase6_resource_restore_displays import TARGETS


def test_resource_restore_display_target_corpus_is_stable():
    assert len(TARGETS) == 8
    assert (5636, 2, "Constitution") in TARGETS
    assert (5637, 2, "Constitution") in TARGETS
    assert (6568, 1, "Undaunted Command") in TARGETS
    assert (6569, 3, "Undaunted Command") in TARGETS
