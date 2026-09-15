from __future__ import annotations

import pytest

from tools.audit_extreme_e2_actual_heal_attribute_denominator import (
    ATTRIBUTE_POINT_TOTAL,
    legal_attribute_allocations,
)


def test_attribute_denominator_enumerates_every_nonnegative_64_point_split() -> None:
    allocations = legal_attribute_allocations()
    expected_count = (ATTRIBUTE_POINT_TOTAL + 1) * (ATTRIBUTE_POINT_TOTAL + 2) // 2

    assert len(allocations) == expected_count == 2145
    assert len(set(allocations)) == expected_count
    assert all(sum(row) == ATTRIBUTE_POINT_TOTAL for row in allocations)
    assert all(min(row) >= 0 for row in allocations)
    assert (64, 0, 0) in allocations
    assert (0, 64, 0) in allocations
    assert (0, 0, 64) in allocations
    assert (22, 21, 21) in allocations


def test_attribute_denominator_supports_other_finite_point_totals() -> None:
    assert legal_attribute_allocations(0) == ((0, 0, 0),)
    assert legal_attribute_allocations(2) == (
        (0, 0, 2),
        (0, 1, 1),
        (0, 2, 0),
        (1, 0, 1),
        (1, 1, 0),
        (2, 0, 0),
    )


def test_attribute_denominator_rejects_negative_point_totals() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        legal_attribute_allocations(-1)
