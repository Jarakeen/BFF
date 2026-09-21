from __future__ import annotations

from services.extreme_sustained_dps_partial_branch_upper_bound_service import (
    ExtremeSustainedDPSBoundEnvelopeInput,
    ExtremeSustainedDPSPartialBranchUpperBoundService,
)
from services.extreme_sustained_dps_pruning_service import (
    ExtremeSustainedDPSBoundEvidence,
)


def _bound(key, value, *, safe=True, unresolved=()):
    return ExtremeSustainedDPSBoundEvidence(
        candidate_key=key,
        upper_bound_dps=value,
        proven_safe=safe,
        source="test",
        unresolved=tuple(unresolved),
    )


def test_multiple_proven_safe_bounds_intersect_by_minimum_not_sum() -> None:
    result = ExtremeSustainedDPSPartialBranchUpperBoundService.compose(
        "branch:a",
        (
            ExtremeSustainedDPSBoundEnvelopeInput(
                "rotation action ceiling",
                _bound("other-key-is-allowed", 200.0),
            ),
            ExtremeSustainedDPSBoundEnvelopeInput(
                "gear dominance ceiling",
                _bound("another-key", 150.0),
            ),
        ),
    )

    assert result.bound.proven_safe is True
    assert result.bound.upper_bound_dps == 150.0
    assert result.accepted_sources == (
        "rotation action ceiling",
        "gear dominance ceiling",
    )


def test_unproven_tighter_number_cannot_override_safe_parent_ceiling() -> None:
    result = ExtremeSustainedDPSPartialBranchUpperBoundService.compose(
        "child",
        (
            ExtremeSustainedDPSBoundEnvelopeInput(
                "heuristic local estimate",
                _bound("local", 80.0, safe=False, unresolved=("not proven",)),
            ),
        ),
        inherited_parent_bound=_bound("parent", 120.0, safe=True),
    )

    assert result.bound.proven_safe is True
    assert result.bound.upper_bound_dps == 120.0
    assert result.accepted_sources == ("inherited parent bound",)
    assert any("heuristic local estimate" in row for row in result.rejected_sources)


def test_child_specific_safe_bound_can_tighten_inherited_parent() -> None:
    result = ExtremeSustainedDPSPartialBranchUpperBoundService.compose(
        "child",
        (
            ExtremeSustainedDPSBoundEnvelopeInput(
                "child exact dominance",
                _bound("child-local", 90.0, safe=True),
            ),
        ),
        inherited_parent_bound=_bound("parent", 120.0, safe=True),
    )

    assert result.bound.proven_safe is True
    assert result.bound.upper_bound_dps == 90.0


def test_missing_all_safe_bounds_remains_forced_open_evidence() -> None:
    result = ExtremeSustainedDPSPartialBranchUpperBoundService.compose(
        "branch:open",
        (
            ExtremeSustainedDPSBoundEnvelopeInput(
                "missing",
                _bound("missing", None, safe=False, unresolved=("no ceiling",)),
            ),
            ExtremeSustainedDPSBoundEnvelopeInput(
                "unsafe",
                _bound("unsafe", 500.0, safe=False, unresolved=("heuristic only",)),
            ),
        ),
    )

    assert result.bound.proven_safe is False
    assert result.bound.upper_bound_dps is None
    assert result.accepted_sources == ()
    assert len(result.rejected_sources) == 2
    assert "missing: no ceiling" in result.unresolved
    assert "unsafe: heuristic only" in result.unresolved


def test_equal_safe_bounds_remain_safe_and_deterministic() -> None:
    result = ExtremeSustainedDPSPartialBranchUpperBoundService.compose(
        "branch:eq",
        (
            ExtremeSustainedDPSBoundEnvelopeInput("B source", _bound("b", 100.0)),
            ExtremeSustainedDPSBoundEnvelopeInput("A source", _bound("a", 100.0)),
        ),
    )

    assert result.bound.proven_safe is True
    assert result.bound.upper_bound_dps == 100.0
    assert "A source" in result.bound.source
