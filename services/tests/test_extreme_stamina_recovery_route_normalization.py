from tools.audit_extreme_stamina_recovery_accelerated_frontier import (
    EXPECTED_LINES,
    _line_id,
)


def test_expected_stamina_route_matches_canonical_lowercase_line_ids():
    service_lines = ("animal_companions", "curative_runeforms", "shadow")
    assert tuple(sorted(_line_id(line) for line in service_lines)) == tuple(sorted(EXPECTED_LINES))


def test_expected_stamina_route_matches_display_line_names_after_normalization():
    display_lines = ("Animal Companions", "Curative Runeforms", "Shadow")
    assert tuple(sorted(_line_id(line) for line in display_lines)) == tuple(sorted(EXPECTED_LINES))
