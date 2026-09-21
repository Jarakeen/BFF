from __future__ import annotations

"""Adapt proven generated gear/progression denominators into canonical axis coverage.

These adapters promote structural search coverage only. They do not claim numeric
action-damage dominance. A denominator may prove that every legal CP loadout, passive
rank state, or dual-bar named-gear realization is represented while still lacking a
safe damage ceiling across those choices.
"""

from dataclasses import dataclass

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    ExtremeSustainedDPSAxisCoverageProof,
)
from services.extreme_sustained_dps_champion_point_frontier_service import (
    ExtremeSustainedDPSChampionPointFrontier,
)
from services.extreme_sustained_dps_dual_bar_gear_frontier_service import (
    ExtremeSustainedDPSDualBarGearFrontier,
)
from services.extreme_sustained_dps_passive_rank_frontier_service import (
    ExtremeSustainedDPSPassiveRankFrontier,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSStructuralAxisCoverageResult:
    proof: ExtremeSustainedDPSAxisCoverageProof
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSGearProgressionAxisCoverageService:
    """Promote only denominator closure that each frontier actually proves."""

    @classmethod
    def dual_bar_gear(
        cls,
        frontier: ExtremeSustainedDPSDualBarGearFrontier,
    ) -> ExtremeSustainedDPSStructuralAxisCoverageResult:
        unresolved = tuple(frontier.unresolved)
        complete = bool(frontier.denominator_proven and not unresolved)
        proof = ExtremeSustainedDPSAxisCoverageProof(
            source="complete sustained-DPS dual-bar named-gear denominator",
            dominated_axes=(
                ("gear_topology", "named_gear_realization")
                if complete
                else ()
            ),
            unresolved=unresolved,
        )
        return ExtremeSustainedDPSStructuralAxisCoverageResult(
            proof=proof,
            evidence=(
                f"Expected gear topology branches: {frontier.expected_topology_count}",
                f"Proven gear topology branches: {frontier.proven_topology_count}",
                f"Legal dual-bar named-gear states: {frontier.dual_bar_state_count}",
                (
                    "Canonical coverage promoted: gear_topology + named_gear_realization"
                    if complete
                    else "Canonical gear-axis coverage withheld"
                ),
                "Traits, enchants, runtime set behavior, and broader weapon-state consequences are not promoted by this proof",
            ),
            unresolved=unresolved,
        )

    @classmethod
    def champion_points(
        cls,
        frontier: ExtremeSustainedDPSChampionPointFrontier,
    ) -> ExtremeSustainedDPSStructuralAxisCoverageResult:
        unresolved = tuple(frontier.unresolved)
        complete = bool(frontier.denominator_proven and not unresolved)
        proof = ExtremeSustainedDPSAxisCoverageProof(
            source="complete sustained-DPS Champion Point denominator",
            dominated_axes=("champion_points",) if complete else (),
            unresolved=unresolved,
        )
        return ExtremeSustainedDPSStructuralAxisCoverageResult(
            proof=proof,
            evidence=(
                f"Champion Point disciplines: {len(frontier.disciplines)}",
                f"Legal CP loadouts: {frontier.candidate_count}",
                (
                    "Canonical coverage promoted: champion_points"
                    if complete
                    else "Canonical Champion Point coverage withheld"
                ),
                "Coverage proves structural CP enumeration only; numeric damage dominance remains separate",
            ),
            unresolved=unresolved,
        )

    @classmethod
    def passive_ranks(
        cls,
        frontier: ExtremeSustainedDPSPassiveRankFrontier,
    ) -> ExtremeSustainedDPSStructuralAxisCoverageResult:
        unresolved = tuple(frontier.unresolved)
        complete = bool(frontier.denominator_proven and not unresolved)
        proof = ExtremeSustainedDPSAxisCoverageProof(
            source="complete sustained-DPS passive-rank denominator",
            dominated_axes=("passive_ranks",) if complete else (),
            unresolved=unresolved,
        )
        return ExtremeSustainedDPSStructuralAxisCoverageResult(
            proof=proof,
            evidence=(
                f"Passive-rank axes: {len(frontier.axes)}",
                f"Legal passive-rank states: {frontier.candidate_count}",
                (
                    "Canonical coverage promoted: passive_ranks"
                    if complete
                    else "Canonical passive-rank coverage withheld"
                ),
                "Coverage proves ranks for explicitly owned combat lines only; racial progression remains separate",
            ),
            unresolved=unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSGearProgressionAxisCoverageService",
    "ExtremeSustainedDPSStructuralAxisCoverageResult",
]
