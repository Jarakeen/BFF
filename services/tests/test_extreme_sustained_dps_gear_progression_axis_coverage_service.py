from __future__ import annotations

import pytest

from types import SimpleNamespace

from services.extreme_sustained_dps_champion_point_frontier_service import (
    ExtremeSustainedDPSChampionPointFrontier,
)
from services.extreme_sustained_dps_gear_progression_axis_coverage_service import (
    ExtremeSustainedDPSGearProgressionAxisCoverageService,
)
from services.extreme_sustained_dps_passive_rank_frontier_service import (
    ExtremeSustainedDPSPassiveRankFrontier,
)


def test_complete_dual_bar_gear_frontier_promotes_only_structural_named_gear_axes() -> None:
    frontier = SimpleNamespace(
        denominator_proven=True,
        unresolved=(),
        expected_topology_count=7,
        proven_topology_count=7,
        dual_bar_state_count=100,
    )

    result = ExtremeSustainedDPSGearProgressionAxisCoverageService.dual_bar_gear(frontier)

    assert result.proof.dominated_axes == (
        "gear_topology",
        "named_gear_realization",
    )
    assert "armor_traits" not in result.proof.dominated_axes
    assert "weapon_enchants" not in result.proof.dominated_axes


def test_incomplete_dual_bar_gear_frontier_promotes_nothing() -> None:
    frontier = SimpleNamespace(
        denominator_proven=False,
        unresolved=("missing topology branch",),
        expected_topology_count=7,
        proven_topology_count=6,
        dual_bar_state_count=80,
    )

    result = ExtremeSustainedDPSGearProgressionAxisCoverageService.dual_bar_gear(frontier)

    assert result.proof.dominated_axes == ()
    assert "missing topology branch" in result.unresolved


def test_complete_cp_frontier_promotes_champion_points_axis_only() -> None:
    frontier = ExtremeSustainedDPSChampionPointFrontier(
        disciplines=(),
        candidate_count=42,
        denominator_proven=True,
        evidence=(),
        unresolved=(),
    )

    result = ExtremeSustainedDPSGearProgressionAxisCoverageService.champion_points(frontier)

    assert result.proof.dominated_axes == ("champion_points",)
    assert result.proof.unresolved == ()


def test_incomplete_cp_frontier_promotes_nothing() -> None:
    frontier = ExtremeSustainedDPSChampionPointFrontier(
        disciplines=(),
        candidate_count=0,
        denominator_proven=False,
        evidence=(),
        unresolved=("CP denominator unresolved",),
    )

    result = ExtremeSustainedDPSGearProgressionAxisCoverageService.champion_points(frontier)

    assert result.proof.dominated_axes == ()
    assert result.unresolved == ("CP denominator unresolved",)


def test_complete_passive_frontier_promotes_passive_rank_axis_only() -> None:
    frontier = ExtremeSustainedDPSPassiveRankFrontier(
        axes=(),
        candidate_count=16,
        denominator_proven=True,
        evidence=(),
        unresolved=(),
    )

    result = ExtremeSustainedDPSGearProgressionAxisCoverageService.passive_ranks(frontier)

    assert result.proof.dominated_axes == ("passive_ranks",)


def test_incomplete_passive_frontier_promotes_nothing() -> None:
    frontier = ExtremeSustainedDPSPassiveRankFrontier(
        axes=(),
        candidate_count=0,
        denominator_proven=False,
        evidence=(),
        unresolved=("passive denominator unresolved",),
    )

    result = ExtremeSustainedDPSGearProgressionAxisCoverageService.passive_ranks(frontier)

    assert result.proof.dominated_axes == ()
    assert "passive denominator unresolved" in result.unresolved


def test_dual_bar_coverage_rejects_truthy_denominator_proof() -> None:
    frontier = SimpleNamespace(
        denominator_proven="true",
        unresolved=(),
        expected_topology_count=1,
        proven_topology_count=1,
        dual_bar_state_count=1,
    )

    with pytest.raises(TypeError, match="denominator_proven must be boolean"):
        ExtremeSustainedDPSGearProgressionAxisCoverageService.dual_bar_gear(frontier)


def test_dual_bar_coverage_rejects_non_tuple_unresolved() -> None:
    frontier = SimpleNamespace(
        denominator_proven=True,
        unresolved=["open"],
        expected_topology_count=1,
        proven_topology_count=1,
        dual_bar_state_count=1,
    )

    with pytest.raises(TypeError, match="unresolved must be a tuple"):
        ExtremeSustainedDPSGearProgressionAxisCoverageService.dual_bar_gear(frontier)


def test_dual_bar_coverage_rejects_boolean_counts() -> None:
    frontier = SimpleNamespace(
        denominator_proven=True,
        unresolved=(),
        expected_topology_count=True,
        proven_topology_count=1,
        dual_bar_state_count=1,
    )

    with pytest.raises(TypeError, match="expected_topology_count must be a non-negative integer"):
        ExtremeSustainedDPSGearProgressionAxisCoverageService.dual_bar_gear(frontier)
