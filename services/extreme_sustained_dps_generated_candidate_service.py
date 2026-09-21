from __future__ import annotations

"""Generate the structural frontier for sustained-DPS global search.

This layer deliberately stops before dynamic build synthesis. It expands only the
finite legality axes already owned by ExtremeGlobalSearchUniverseService and keeps
all deferred dynamic axes explicit. Later generators may refine one structural
candidate with gear, traits, glyphs, skills, CP, consumables, passives, and runtime
state without re-enumerating the structural denominator.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.character_progression import AttributeAllocation
from services.extreme_global_search_universe_service import (
    ExtremeGlobalSearchUniverse,
    ExtremeGlobalSearchUniverseService,
)
from services.extreme_heal_class_route_service import ExtremeHealClassRoute


@dataclass(frozen=True)
class ExtremeSustainedDPSStructuralCandidate:
    structural_index: int
    race: str
    class_route: ExtremeHealClassRoute
    attributes: AttributeAllocation
    active_bar: str


@dataclass(frozen=True)
class ExtremeSustainedDPSGeneratedFrontier:
    structural_candidate_count: int
    structural_denominator_proven: bool
    expanded_axes: tuple[str, ...]
    deferred_axes: tuple[str, ...]
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def generated_search_complete(self) -> bool:
        return self.structural_denominator_proven and not self.deferred_axes and not self.unresolved


class ExtremeSustainedDPSGeneratedCandidateService:
    """Expose a deterministic, pageable structural candidate frontier."""

    EXPANDED_AXES = (
        "race",
        "legal class route",
        "64-point attribute allocation",
        "active bar",
    )

    def __init__(
        self,
        database_path: str | Path,
        *,
        universe_service: ExtremeGlobalSearchUniverseService | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.universe_service = universe_service or ExtremeGlobalSearchUniverseService(
            self.database_path
        )

    def frontier(self) -> ExtremeSustainedDPSGeneratedFrontier:
        universe = self.universe_service.build()
        count = self._candidate_count(universe)
        unresolved: list[str] = []
        if not universe.structural_denominator_proven:
            unresolved.append(
                "Structural Extreme denominator is incomplete; generated sustained-DPS frontier is not globally enumerable yet"
            )
        if count <= 0:
            unresolved.append("Generated sustained-DPS structural frontier is empty")

        evidence = (
            f"Structural candidate count: {count}",
            f"Race count: {len(universe.races)}",
            f"Legal class-route count: {len(universe.class_routes)}",
            f"Attribute-allocation count: {len(universe.attribute_allocations)}",
            f"Active-bar count: {len(universe.active_bars)}",
            "Structural candidates are coordinates only; no gear, skills, CP, consumables, passives, or rotations are fabricated",
        )
        return ExtremeSustainedDPSGeneratedFrontier(
            structural_candidate_count=count,
            structural_denominator_proven=bool(universe.structural_denominator_proven),
            expanded_axes=self.EXPANDED_AXES,
            deferred_axes=tuple(universe.deferred_dynamic_axes),
            evidence=evidence,
            unresolved=tuple(unresolved),
        )

    def candidate_at(self, index: int) -> ExtremeSustainedDPSStructuralCandidate:
        universe = self.universe_service.build()
        return self._candidate_from_universe(universe, index)

    @classmethod
    def _candidate_from_universe(
        cls,
        universe: ExtremeGlobalSearchUniverse,
        index: int,
    ) -> ExtremeSustainedDPSStructuralCandidate:
        count = cls._candidate_count(universe)
        position = int(index)
        if position < 0 or position >= count:
            raise IndexError(
                f"generated sustained-DPS structural candidate index {position} outside 0..{max(count - 1, 0)}"
            )

        bars = len(universe.active_bars)
        attrs = len(universe.attribute_allocations)
        routes = len(universe.class_routes)

        active_bar_index = position % bars
        quotient = position // bars
        attribute_index = quotient % attrs
        quotient //= attrs
        class_route_index = quotient % routes
        race_index = quotient // routes

        return ExtremeSustainedDPSStructuralCandidate(
            structural_index=position,
            race=universe.races[race_index],
            class_route=universe.class_routes[class_route_index],
            attributes=universe.attribute_allocations[attribute_index],
            active_bar=universe.active_bars[active_bar_index],
        )

    def page(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[ExtremeSustainedDPSStructuralCandidate, ...]:
        start = max(0, int(offset))
        size = max(0, int(limit))
        if size == 0:
            return ()
        universe = self.universe_service.build()
        count = self._candidate_count(universe)
        stop = min(count, start + size)
        return tuple(
            self._candidate_from_universe(universe, index)
            for index in range(start, stop)
        )

    @staticmethod
    def _candidate_count(universe: ExtremeGlobalSearchUniverse) -> int:
        return (
            len(universe.races)
            * len(universe.class_routes)
            * len(universe.attribute_allocations)
            * len(universe.active_bars)
        )


__all__ = [
    "ExtremeSustainedDPSGeneratedCandidateService",
    "ExtremeSustainedDPSGeneratedFrontier",
    "ExtremeSustainedDPSStructuralCandidate",
]
