from __future__ import annotations

from services.extreme_sustained_dps_generated_candidate_service import (
    ExtremeSustainedDPSGeneratedFrontier,
)
from services.extreme_sustained_dps_structural_axis_coverage_service import (
    ExtremeSustainedDPSStructuralAxisCoverageService,
)


def _frontier(*, proven=True, unresolved=()):
    return ExtremeSustainedDPSGeneratedFrontier(
        structural_candidate_count=24,
        structural_denominator_proven=proven,
        expanded_axes=(
            "race",
            "legal class route",
            "64-point attribute allocation",
            "active bar",
        ),
        deferred_axes=("gear", "skills", "rotation"),
        evidence=(),
        unresolved=tuple(unresolved),
    )


def test_structural_frontier_promotes_race_class_route_and_attributes_only() -> None:
    result = ExtremeSustainedDPSStructuralAxisCoverageService.from_frontier(
        _frontier()
    )

    assert result.proof.dominated_axes == (
        "race",
        "class_route",
        "attributes",
    )
    assert result.proof.omitted_scope == ()
    assert result.unresolved == ()
    assert any("active-bar coordinate is not promoted" in row for row in result.evidence)
    assert any("does not prove those coordinates are wired" in row for row in result.evidence)


def test_unproven_structural_frontier_promotes_no_axes() -> None:
    result = ExtremeSustainedDPSStructuralAxisCoverageService.from_frontier(
        _frontier(proven=False)
    )

    assert result.proof.dominated_axes == ()


def test_structural_frontier_missing_expected_coordinate_fails_closed() -> None:
    frontier = ExtremeSustainedDPSGeneratedFrontier(
        structural_candidate_count=12,
        structural_denominator_proven=True,
        expanded_axes=(
            "race",
            "legal class route",
            "64-point attribute allocation",
        ),
        deferred_axes=(),
        evidence=(),
        unresolved=(),
    )

    result = ExtremeSustainedDPSStructuralAxisCoverageService.from_frontier(
        frontier
    )

    assert result.proof.dominated_axes == ()
    assert any("active bar" in row for row in result.unresolved)
