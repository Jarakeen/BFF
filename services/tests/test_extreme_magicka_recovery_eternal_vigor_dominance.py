from types import SimpleNamespace

import pytest

from tools.audit_extreme_magicka_recovery_eternal_vigor_dominance import (
    exact_eternal_vigor_special_flat,
    final_upper,
)


def test_final_upper_composes_structural_and_exact_special_before_multiplier():
    result = final_upper(
        shared_flat=3702.294,
        structural=816.0,
        special=337.0,
    )

    assert result == pytest.approx((3702.294 + 816.0 + 337.0) * 1.81)


def test_exact_eternal_vigor_special_uses_five_piece_increment_not_cumulative_sum():
    evidence = SimpleNamespace(
        set_name="Eternal Vigor",
        piece_count=5,
        candidate=SimpleNamespace(
            source_bonuses=(
                SimpleNamespace(description="Adds 129 Magicka Recovery"),
                SimpleNamespace(
                    description=(
                        "Adds 337 Stamina and Magicka Recovery while your Health is above 50%. "
                        "Adds 1011 Health Recovery while your Health is 50% or less."
                    )
                ),
            )
        ),
    )

    assert exact_eternal_vigor_special_flat(evidence) == pytest.approx(337.0)


def test_physical_five_piece_structure_with_exact_special_loses_to_willow():
    willow = 9259.238
    result = final_upper(
        shared_flat=3702.294,
        structural=821.59,
        special=337.0,
    )

    assert result < willow


def test_generic_overcount_survives_as_expected_control():
    willow = 9259.238
    result = final_upper(
        shared_flat=3702.294,
        structural=821.59,
        special=595.0,
    )

    assert result > willow
