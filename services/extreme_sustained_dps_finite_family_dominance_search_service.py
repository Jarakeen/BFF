from __future__ import annotations

"""Reusable numeric dominance searches for CP, passive-rank, and dual-bar gear axes.

This service owns composition only:
finite generated frontier -> lazy indexed adapter -> canonical exact-action evaluator
-> generic finite-axis action dominance.

No ESO damage formula, frontier enumeration rule, or proof arithmetic is reimplemented.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_champion_point_frontier_service import (
    ExtremeSustainedDPSChampionPointFrontierService,
)
from services.extreme_sustained_dps_dual_bar_gear_frontier_service import (
    ExtremeSustainedDPSDualBarGearFrontier,
)
from services.extreme_sustained_dps_finite_axis_action_dominance_service import (
    ExtremeSustainedDPSFiniteAxisActionDominanceResult,
    ExtremeSustainedDPSFiniteAxisActionDominanceService,
)
from services.extreme_sustained_dps_finite_axis_canonical_action_evaluator_service import (
    ExtremeSustainedDPSExactActionScenario,
    ExtremeSustainedDPSFiniteAxisCanonicalActionEvaluatorService,
)
from services.extreme_sustained_dps_finite_axis_frontier_adapter_service import (
    ExtremeSustainedDPSFiniteAxisFrontierAdapterService,
)
from services.extreme_sustained_dps_passive_rank_frontier_service import (
    ExtremeSustainedDPSPassiveRankFrontierService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSFiniteFamilyDominanceInputs:
    baseline_build: PlayerBuild
    baseline_progression: CharacterProgression
    scenario: ExtremeSustainedDPSExactActionScenario


class ExtremeSustainedDPSFiniteFamilyDominanceSearchService:
    """Compose existing frontier/evaluator/proof authorities into reusable searches."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        inputs: ExtremeSustainedDPSFiniteFamilyDominanceInputs,
    ) -> None:
        self.database_path = Path(database_path)
        self.inputs = inputs

    def _evaluators(self) -> ExtremeSustainedDPSFiniteAxisCanonicalActionEvaluatorService:
        return ExtremeSustainedDPSFiniteAxisCanonicalActionEvaluatorService(
            self.database_path,
            baseline_build=self.inputs.baseline_build,
            baseline_progression=self.inputs.baseline_progression,
            scenario=self.inputs.scenario,
        )

    def champion_points(
        self,
        *,
        candidate_key: str,
        frontier_service: ExtremeSustainedDPSChampionPointFrontierService,
    ) -> ExtremeSustainedDPSFiniteAxisActionDominanceResult:
        frontier = ExtremeSustainedDPSFiniteAxisFrontierAdapterService.champion_points(
            frontier_service,
            self.inputs.baseline_build,
        )
        return ExtremeSustainedDPSFiniteAxisActionDominanceService.evaluate_indexed(
            candidate_key=candidate_key,
            frontier=frontier,
            evaluator=self._evaluators().champion_points(),
            source="canonical finite Champion Point exact-action dominance search",
        )

    def passive_ranks(
        self,
        *,
        candidate_key: str,
        frontier_service: ExtremeSustainedDPSPassiveRankFrontierService,
        character_class: str,
    ) -> ExtremeSustainedDPSFiniteAxisActionDominanceResult:
        frontier = ExtremeSustainedDPSFiniteAxisFrontierAdapterService.passive_ranks(
            frontier_service,
            self.inputs.baseline_progression,
            character_class=character_class,
        )
        return ExtremeSustainedDPSFiniteAxisActionDominanceService.evaluate_indexed(
            candidate_key=candidate_key,
            frontier=frontier,
            evaluator=self._evaluators().passive_ranks(),
            source="canonical finite passive-rank exact-action dominance search",
        )

    def dual_bar_gear(
        self,
        *,
        candidate_key: str,
        frontier: ExtremeSustainedDPSDualBarGearFrontier,
    ) -> ExtremeSustainedDPSFiniteAxisActionDominanceResult:
        indexed = ExtremeSustainedDPSFiniteAxisFrontierAdapterService.dual_bar_gear(
            frontier
        )
        return ExtremeSustainedDPSFiniteAxisActionDominanceService.evaluate_indexed(
            candidate_key=candidate_key,
            frontier=indexed,
            evaluator=self._evaluators().dual_bar_gear(),
            source="canonical finite dual-bar named-gear exact-action dominance search",
        )


__all__ = [
    "ExtremeSustainedDPSFiniteFamilyDominanceInputs",
    "ExtremeSustainedDPSFiniteFamilyDominanceSearchService",
]
