from __future__ import annotations

"""Concrete indexed-axis adapters for late generated sustained-DPS refinement.

This adapter pack connects the existing Champion Point, potion, passive-rank, and
two-bar skill frontiers to the generic generated-frontier tree. The selected axis
objects remain separate until the final skill coordinate is known, then the canonical
candidate assembly service copies only each frontier's owned state onto the shared
cross-axis context.
"""

from dataclasses import dataclass, replace

from services.extreme_sustained_dps_champion_point_frontier_service import (
    ExtremeSustainedDPSChampionPointCandidate,
    ExtremeSustainedDPSChampionPointFrontierService,
)
from services.extreme_sustained_dps_cross_axis_context_service import (
    ExtremeSustainedDPSCrossAxisContext,
)
from services.extreme_sustained_dps_generated_candidate_assembly_service import (
    ExtremeSustainedDPSAssembledCandidate,
    ExtremeSustainedDPSGeneratedCandidateAssemblyService,
)
from services.extreme_sustained_dps_generated_frontier_wiring_service import (
    ExtremeSustainedDPSIndexedFrontierAxis,
)
from services.extreme_sustained_dps_passive_rank_frontier_service import (
    ExtremeSustainedDPSPassiveRankCandidate,
    ExtremeSustainedDPSPassiveRankFrontierService,
)
from services.extreme_sustained_dps_potion_frontier_service import (
    ExtremeSustainedDPSPotionCandidate,
    ExtremeSustainedDPSPotionFrontierService,
)
from services.extreme_sustained_dps_skill_bar_frontier_service import (
    ExtremeSustainedDPSSkillBarFrontierService,
    ExtremeSustainedDPSTwoBarSkillCandidate,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedLateAxisState:
    context: ExtremeSustainedDPSCrossAxisContext
    champion_points: ExtremeSustainedDPSChampionPointCandidate | None = None
    potion: ExtremeSustainedDPSPotionCandidate | None = None
    passive_ranks: ExtremeSustainedDPSPassiveRankCandidate | None = None
    skills: ExtremeSustainedDPSTwoBarSkillCandidate | None = None
    assembled: ExtremeSustainedDPSAssembledCandidate | None = None

    @property
    def complete(self) -> bool:
        return self.assembled is not None


class ExtremeSustainedDPSGeneratedLateAxisAdapterService:
    """Adapt CP → potion → passives → skills into indexed search-tree axes."""

    def __init__(
        self,
        *,
        champion_points: ExtremeSustainedDPSChampionPointFrontierService | object,
        potions: ExtremeSustainedDPSPotionFrontierService | object,
        passive_ranks: ExtremeSustainedDPSPassiveRankFrontierService | object,
        skill_bars: ExtremeSustainedDPSSkillBarFrontierService | object,
        assembly: ExtremeSustainedDPSGeneratedCandidateAssemblyService | object = (
            ExtremeSustainedDPSGeneratedCandidateAssemblyService
        ),
    ) -> None:
        self.champion_points = champion_points
        self.potions = potions
        self.passive_ranks = passive_ranks
        self.skill_bars = skill_bars
        self.assembly = assembly

    @staticmethod
    def _proven_count(frontier: object, label: str) -> int:
        count = int(getattr(frontier, "candidate_count", 0))
        unresolved = tuple(getattr(frontier, "unresolved", ()) or ())
        if not bool(getattr(frontier, "denominator_proven", False)):
            detail = "; ".join(str(item) for item in unresolved if str(item))
            raise ValueError(
                f"{label} denominator is unresolved"
                + (f": {detail}" if detail else "")
            )
        if count <= 0:
            raise ValueError(f"{label} denominator is empty")
        return count

    def _cp_count(self, _state: object) -> int:
        return self._proven_count(
            self.champion_points.frontier(),
            "Champion Point frontier",
        )

    def _cp_at(
        self,
        state: ExtremeSustainedDPSGeneratedLateAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedLateAxisState:
        candidate = self.champion_points.candidate_at(state.context.build, index)
        return replace(state, champion_points=candidate)

    def _potion_count(self, _state: object) -> int:
        return self._proven_count(
            self.potions.frontier(),
            "potion frontier",
        )

    def _potion_at(
        self,
        state: ExtremeSustainedDPSGeneratedLateAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedLateAxisState:
        candidate = self.potions.candidate_at(state.context.build, index)
        return replace(state, potion=candidate)

    def _passive_count(
        self,
        state: ExtremeSustainedDPSGeneratedLateAxisState,
    ) -> int:
        frontier = self.passive_ranks.frontier(
            state.context.progression,
            character_class=state.context.build.EsoClass,
        )
        return self._proven_count(frontier, "passive-rank frontier")

    def _passive_at(
        self,
        state: ExtremeSustainedDPSGeneratedLateAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedLateAxisState:
        candidate = self.passive_ranks.candidate_at(
            state.context.progression,
            character_class=state.context.build.EsoClass,
            index=index,
        )
        return replace(state, passive_ranks=candidate)

    def _skill_count(
        self,
        state: ExtremeSustainedDPSGeneratedLateAxisState,
    ) -> int:
        frontier = self.skill_bars.frontier(
            front_context=state.context.front_skill_context,
            back_context=state.context.back_skill_context,
            one_bar_only=state.context.one_bar_only,
        )
        return self._proven_count(frontier, "skill-bar frontier")

    def _skill_at(
        self,
        state: ExtremeSustainedDPSGeneratedLateAxisState,
        index: int,
    ) -> ExtremeSustainedDPSGeneratedLateAxisState:
        if (
            state.champion_points is None
            or state.potion is None
            or state.passive_ranks is None
        ):
            raise ValueError(
                "generated late-axis assembly requires CP, potion, and passive selections before skills"
            )
        skills = self.skill_bars.candidate_at(
            state.context.build,
            front_context=state.context.front_skill_context,
            back_context=state.context.back_skill_context,
            index=index,
            one_bar_only=state.context.one_bar_only,
        )
        assembled = self.assembly.assemble(
            state.context,
            champion_points=state.champion_points,
            potion=state.potion,
            passive_ranks=state.passive_ranks,
            skills=skills,
        )
        return replace(state, skills=skills, assembled=assembled)

    def root(
        self,
        context: ExtremeSustainedDPSCrossAxisContext,
    ) -> ExtremeSustainedDPSGeneratedLateAxisState:
        return ExtremeSustainedDPSGeneratedLateAxisState(context=context)

    def axes(self) -> tuple[ExtremeSustainedDPSIndexedFrontierAxis, ...]:
        return (
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Champion Points",
                candidate_count=self._cp_count,
                candidate_at=self._cp_at,
                canonical_axes=("champion_points",),
            ),
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Potion Family",
                candidate_count=self._potion_count,
                candidate_at=self._potion_at,
                canonical_axes=("potion_selection",),
            ),
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Passive Ranks",
                candidate_count=self._passive_count,
                candidate_at=self._passive_at,
                canonical_axes=("passive_ranks",),
            ),
            ExtremeSustainedDPSIndexedFrontierAxis(
                "Skill Bars",
                candidate_count=self._skill_count,
                candidate_at=self._skill_at,
                canonical_axes=("skill_bars",),
            ),
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedLateAxisAdapterService",
    "ExtremeSustainedDPSGeneratedLateAxisState",
]
