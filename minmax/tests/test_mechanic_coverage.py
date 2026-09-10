from __future__ import annotations

import pytest

from minmax.mechanic_coverage import (
    MechanicCoverageItem,
    summarize_mechanic_coverage,
    validate_mechanic_coverage,
)


def _row(mechanic_id: str, status: str, *, category: str = "shared") -> MechanicCoverageItem:
    return MechanicCoverageItem(
        mechanic_id=mechanic_id,
        category=category,
        status=status,
        evidence="test evidence",
        detail="test detail",
    )


def test_conditional_proven_mechanics_count_as_supported_coverage() -> None:
    summary = summarize_mechanic_coverage(
        (
            _row("standing", "implemented"),
            _row("explicit_runtime_window", "conditional"),
            _row("missing_provenance", "unresolved"),
            _row("not_this_objective", "irrelevant"),
        )
    )

    assert summary.denominator == 3
    assert summary.covered == 2
    assert summary.implemented == 1
    assert summary.conditional == 1
    assert summary.unresolved == 1
    assert summary.irrelevant == 1
    assert summary.blocker_ids == ("missing_provenance",)
    assert summary.coverage_fraction == pytest.approx(2 / 3)
    assert not summary.complete


def test_only_unresolved_mechanics_block_completion() -> None:
    summary = summarize_mechanic_coverage(
        (
            _row("standing", "implemented"),
            _row("explicit_target_state", "conditional"),
            _row("outside_objective", "irrelevant"),
        )
    )

    assert summary.denominator == 2
    assert summary.covered == 2
    assert summary.blocker_ids == ()
    assert summary.coverage_fraction == 1.0
    assert summary.complete


def test_coverage_summary_is_deterministic_and_preserves_blocker_order() -> None:
    rows = (
        _row("first_gap", "unresolved"),
        _row("covered", "implemented"),
        _row("second_gap", "unresolved"),
    )

    first = summarize_mechanic_coverage(rows)
    second = summarize_mechanic_coverage(rows)

    assert first == second
    assert first.blocker_ids == ("first_gap", "second_gap")


def test_coverage_validation_rejects_duplicate_ids_invalid_status_and_missing_categories() -> None:
    with pytest.raises(ValueError, match="duplicate mechanic ids"):
        validate_mechanic_coverage((_row("same", "implemented"), _row("same", "conditional")))

    with pytest.raises(ValueError, match="invalid status"):
        validate_mechanic_coverage((_row("bad", "mystery"),))

    with pytest.raises(ValueError, match="missing required categories"):
        validate_mechanic_coverage(
            (_row("present", "implemented", category="present"),),
            required_categories=("present", "required_elsewhere"),
        )
