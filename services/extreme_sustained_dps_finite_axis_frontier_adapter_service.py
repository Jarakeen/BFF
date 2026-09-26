from __future__ import annotations

"""Lazy concrete frontier adapters for generic sustained-DPS finite-axis dominance."""

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_champion_point_frontier_service import (
    ExtremeSustainedDPSChampionPointCandidate,
    ExtremeSustainedDPSChampionPointFrontierService,
)
from services.extreme_sustained_dps_dual_bar_gear_frontier_service import (
    ExtremeSustainedDPSDualBarGearFrontier,
)
from services.extreme_sustained_dps_finite_axis_action_dominance_service import (
    ExtremeSustainedDPSFiniteAxisChoice,
)
from services.extreme_sustained_dps_passive_rank_frontier_service import (
    ExtremeSustainedDPSPassiveRankCandidate,
    ExtremeSustainedDPSPassiveRankFrontierService,
)
from services.extreme_dual_bar_gear_state_service import ExtremeDualBarGearState


T = TypeVar("T")


@dataclass(frozen=True)
class ExtremeSustainedDPSIndexedChoiceAdapter(Generic[T]):
    axes: tuple[str, ...]
    choice_count: int
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]
    _prefix: str
    _resolver: Callable[[int], T]

    def __post_init__(self) -> None:
        if not isinstance(self.axes, tuple):
            raise TypeError("indexed finite-axis adapter axes must be a tuple")
        if isinstance(self.choice_count, bool) or not isinstance(self.choice_count, int):
            raise TypeError("indexed finite-axis adapter choice_count must be an integer")
        if self.choice_count < 0:
            raise ValueError("indexed finite-axis adapter choice_count cannot be negative")
        if not isinstance(self.denominator_proven, bool):
            raise TypeError("indexed finite-axis adapter denominator_proven must be boolean")
        if not isinstance(self.evidence, tuple):
            raise TypeError("indexed finite-axis adapter evidence must be a tuple")
        if not isinstance(self.unresolved, tuple):
            raise TypeError("indexed finite-axis adapter unresolved must be a tuple")
        if not isinstance(self._prefix, str) or not self._prefix.strip():
            raise ValueError("indexed finite-axis adapter prefix cannot be empty")
        if not callable(self._resolver):
            raise TypeError("indexed finite-axis adapter resolver must be callable")
        object.__setattr__(self, "_prefix", self._prefix.strip())

    def choice_at(self, index: int) -> ExtremeSustainedDPSFiniteAxisChoice[T]:
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("indexed finite-axis adapter choice index must be an integer")
        if index < 0 or index >= self.choice_count:
            raise IndexError("indexed finite-axis adapter choice index out of range")
        return ExtremeSustainedDPSFiniteAxisChoice(
            choice_id=f"{self._prefix}:{index}",
            payload=self._resolver(index),
        )


class ExtremeSustainedDPSFiniteAxisFrontierAdapterService:
    """Expose existing generated frontiers through the indexed dominance contract."""

    @classmethod
    def champion_points(
        cls,
        frontier_service: ExtremeSustainedDPSChampionPointFrontierService,
        baseline_build: PlayerBuild,
    ) -> ExtremeSustainedDPSIndexedChoiceAdapter[ExtremeSustainedDPSChampionPointCandidate]:
        frontier = frontier_service.frontier()
        return ExtremeSustainedDPSIndexedChoiceAdapter(
            axes=("champion_points",),
            choice_count=frontier.candidate_count,
            denominator_proven=frontier.denominator_proven,
            evidence=frontier.evidence,
            unresolved=frontier.unresolved,
            _prefix="cp",
            _resolver=lambda index: frontier_service.candidate_at(baseline_build, index),
        )

    @classmethod
    def passive_ranks(
        cls,
        frontier_service: ExtremeSustainedDPSPassiveRankFrontierService,
        progression: CharacterProgression,
        *,
        character_class: str,
    ) -> ExtremeSustainedDPSIndexedChoiceAdapter[ExtremeSustainedDPSPassiveRankCandidate]:
        frontier = frontier_service.frontier(
            progression,
            character_class=character_class,
        )
        return ExtremeSustainedDPSIndexedChoiceAdapter(
            axes=("passive_ranks",),
            choice_count=frontier.candidate_count,
            denominator_proven=frontier.denominator_proven,
            evidence=frontier.evidence,
            unresolved=frontier.unresolved,
            _prefix="passive",
            _resolver=lambda index: frontier_service.candidate_at(
                progression,
                character_class=character_class,
                index=index,
            ),
        )

    @classmethod
    def dual_bar_gear(
        cls,
        frontier: ExtremeSustainedDPSDualBarGearFrontier,
    ) -> ExtremeSustainedDPSIndexedChoiceAdapter[ExtremeDualBarGearState]:
        states = frontier.catalog.states
        return ExtremeSustainedDPSIndexedChoiceAdapter(
            axes=("gear_topology", "named_gear_realization"),
            choice_count=len(states),
            denominator_proven=frontier.denominator_proven,
            evidence=frontier.evidence,
            unresolved=frontier.unresolved,
            _prefix="gear",
            _resolver=lambda index: states[index],
        )


__all__ = [
    "ExtremeSustainedDPSFiniteAxisFrontierAdapterService",
    "ExtremeSustainedDPSIndexedChoiceAdapter",
]
