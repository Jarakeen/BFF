from __future__ import annotations

"""Score the complete objective-neutral Extreme structural universe.

This layer deliberately owns no ESO formulas.  It combines the finite legality
axes from :mod:`extreme_global_search_universe_service` and delegates objective
math to one injected canonical scorer.  That separation matters: Extreme owns
exhaustive search, while shared mechanics services remain the sole authority for
what a candidate actually scores.

The result is still *structural* evidence only.  Deferred dynamic axes such as
gear topology, skill choices, CP, consumables, and runtime state remain explicit
unless the injected scorer supplies proof-owned closure metadata for an axis it
actually executes.
"""

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from minmax.character_progression import AttributeAllocation
from services.extreme_global_search_universe_service import (
    ExtremeGlobalSearchUniverse,
    ExtremeGlobalSearchUniverseService,
)
from services.extreme_heal_class_route_service import ExtremeHealClassRoute


ScorePayload = TypeVar("ScorePayload")


@dataclass(frozen=True)
class ExtremeStructuralCandidate:
    race: str
    class_route: ExtremeHealClassRoute
    attributes: AttributeAllocation
    active_bar: str

    @property
    def identity(self) -> tuple[str, str, tuple[str, ...], int, int, int, str]:
        return (
            self.race,
            self.class_route.base_class.value,
            tuple(self.class_route.equipped_skill_lines),
            int(self.attributes.health),
            int(self.attributes.magicka),
            int(self.attributes.stamina),
            self.active_bar,
        )


@dataclass(frozen=True)
class ExtremeStructuralScore(Generic[ScorePayload]):
    candidate: ExtremeStructuralCandidate
    value: float
    payload: ScorePayload | None = None
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtremeStructuralGlobalSearchResult(Generic[ScorePayload]):
    objective_key: str
    best: ExtremeStructuralScore[ScorePayload] | None
    candidates_scored: int
    ties_at_best: int
    structural_scope: tuple[str, ...]
    deferred_dynamic_axes: tuple[str, ...]
    structural_denominator_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def global_denominator_proven(self) -> bool:
        # Structural completeness is necessary but never sufficient while any
        # dynamic build/runtime axis remains deferred.
        return self.structural_denominator_proven and not self.deferred_dynamic_axes


StructuralScorer = Callable[
    [str, ExtremeStructuralCandidate],
    tuple[float, ScorePayload | None, tuple[str, ...]],
]


class ExtremeStructuralGlobalSearchService(Generic[ScorePayload]):
    """Exhaustively score race × class route × attributes × active bar.

    Candidate ordering is deterministic and ties retain the lexicographically
    smallest structural identity.  This makes repeated audits reproducible while
    still exposing how many structurally distinct candidates share the best value.

    Scorers may optionally expose ``closed_dynamic_axes(objective_key)`` and
    ``additional_search_scope(objective_key)``.  These hooks carry proof metadata
    only; the generic structural search does not interpret ESO mechanics itself.
    """

    def __init__(
        self,
        universe_service: ExtremeGlobalSearchUniverseService,
        *,
        scorer: StructuralScorer[ScorePayload],
    ) -> None:
        self.universe_service = universe_service
        self.scorer = scorer

    @staticmethod
    def candidate_count(universe: ExtremeGlobalSearchUniverse) -> int:
        return (
            len(universe.races)
            * len(universe.class_routes)
            * len(universe.attribute_allocations)
            * len(universe.active_bars)
        )

    def _scorer_metadata(self, name: str, objective_key: str) -> tuple[str, ...]:
        resolver = getattr(self.scorer, name, None)
        if not callable(resolver):
            return ()
        values = resolver(objective_key)
        return tuple(
            dict.fromkeys(
                str(value).strip()
                for value in tuple(values or ())
                if str(value).strip()
            )
        )

    def search(self, objective_key: str) -> ExtremeStructuralGlobalSearchResult[ScorePayload]:
        key = str(objective_key or "").strip().casefold()
        if not key:
            raise ValueError("Extreme structural search objective_key is required")

        universe = self.universe_service.build()
        best: ExtremeStructuralScore[ScorePayload] | None = None
        best_value: float | None = None
        ties = 0
        scored = 0
        unresolved: list[str] = []

        for race in universe.races:
            for route in universe.class_routes:
                for attributes in universe.attribute_allocations:
                    for active_bar in universe.active_bars:
                        candidate = ExtremeStructuralCandidate(
                            race=race,
                            class_route=route,
                            attributes=attributes,
                            active_bar=active_bar,
                        )
                        value, payload, candidate_unresolved = self.scorer(key, candidate)
                        score = ExtremeStructuralScore(
                            candidate=candidate,
                            value=float(value),
                            payload=payload,
                            unresolved=tuple(candidate_unresolved or ()),
                        )
                        scored += 1
                        unresolved.extend(score.unresolved)

                        if best_value is None or score.value > best_value + 1e-9:
                            best = score
                            best_value = score.value
                            ties = 1
                            continue
                        if abs(score.value - best_value) <= 1e-9:
                            ties += 1
                            if best is None or score.candidate.identity < best.candidate.identity:
                                best = score

        expected = self.candidate_count(universe)
        structural_proven = bool(
            universe.structural_denominator_proven
            and expected > 0
            and scored == expected
        )
        closed_axes = frozenset(self._scorer_metadata("closed_dynamic_axes", key))
        additional_scope = self._scorer_metadata("additional_search_scope", key)
        return ExtremeStructuralGlobalSearchResult(
            objective_key=key,
            best=best,
            candidates_scored=scored,
            ties_at_best=ties,
            structural_scope=tuple(
                dict.fromkeys((*universe.structural_scope, *additional_scope))
            ),
            deferred_dynamic_axes=tuple(
                axis for axis in universe.deferred_dynamic_axes if axis not in closed_axes
            ),
            structural_denominator_proven=structural_proven,
            unresolved=tuple(dict.fromkeys(message for message in unresolved if message)),
        )
