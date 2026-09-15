from __future__ import annotations

from tools.audit_extreme_e2_actual_heal_armor_search import (
    armor_weight_signature,
    expected_raw_layout_count,
)


def test_expected_raw_layout_count_multiplies_slot_option_denominator() -> None:
    options = (("Light", "Medium", "Heavy"),) * 7

    assert expected_raw_layout_count(options) == 3 ** 7 == 2187


def test_expected_raw_layout_count_fails_closed_for_missing_slot_options() -> None:
    assert expected_raw_layout_count(()) == 0
    assert expected_raw_layout_count((("Light",), (), ("Heavy",))) == 0


def test_armor_weight_signature_preserves_reviewed_h1_state_only() -> None:
    assert armor_weight_signature(("Light",) * 7) == (0, 1)
    assert armor_weight_signature(("Medium",) * 7) == (7, 1)
    assert armor_weight_signature(
        ("Medium", "Medium", "Light", "Heavy", "Light", "Heavy", "Light")
    ) == (2, 3)


def test_armor_weight_signature_normalizes_case_and_spacing() -> None:
    assert armor_weight_signature((" medium ", "LIGHT", "heavy")) == (1, 3)
