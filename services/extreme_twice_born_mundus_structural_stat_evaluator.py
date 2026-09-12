from __future__ import annotations

"""Finite Mundus search for an active Twice-Born Star 5-piece realization.

Ordinary objectives retain the full legal zero/one/two-Mundus state space. For
Max Magicka / Max Stamina, the shared resource Mundus proof may collapse that
space to the unique target-resource witness when every other Mundus is proven
irrelevant to the requested maximum.
"""

from collections.abc import Callable
from itertools import combinations
from typing import Any

from minmax.mundus_repository import MundusRepository
from services.extreme_resource_mundus_projection_service import (
    ExtremeResourceMundusProjection,
    ExtremeResourceMundusProjectionService,
)
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate


class ExtremeTwiceBornMundusStructuralStatEvaluator:
    """Score legal TBS Mundus states with exact max-resource reduction."""

    def __init__(
        self,
        *,
        evaluator: Any,
        mundus_repository: MundusRepository,
        second_mundus_setter: Callable[[str], None] | None = None,
    ) -> None:
        self.evaluator = evaluator
        self.mundus_repository = mundus_repository
        self.second_mundus_setter = second_mundus_setter
        self._projection_cache: dict[str, ExtremeResourceMundusProjection] = {}

    def mundus_projection(self, objective_key: str) -> ExtremeResourceMundusProjection | None:
        key = str(objective_key or "").strip().casefold()
        if key not in ExtremeResourceMundusProjectionService.SUPPORTED_OBJECTIVES:
            return None
        cached = self._projection_cache.get(key)
        if cached is None:
            cached = ExtremeResourceMundusProjectionService(self.mundus_repository).build(key)
            self._projection_cache[key] = cached
        return cached

    def mundus_choices(self) -> tuple[str, ...]:
        values: list[str] = []
        seen: set[str] = set()
        for raw in self.mundus_repository.list_names():
            name = str(raw or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            values.append(name)
        return tuple(values)

    def mundus_states(self, objective_key: str | None = None) -> tuple[tuple[str, str], ...]:
        key = str(objective_key or "").strip().casefold()
        if key:
            projection = self.mundus_projection(key)
            if projection is not None and projection.projection_complete:
                return ((str(projection.witness), ""),)

        choices = self.mundus_choices()
        states: list[tuple[str, str]] = [("", "")]
        states.extend((name, "") for name in choices)
        states.extend(tuple(pair) for pair in combinations(choices, 2))
        return tuple(states)

    def __call__(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]:
        return self.evaluate_candidate(objective_key, candidate)

    def evaluate_candidate(
        self,
        objective_key: str,
        candidate: ExtremeStructuralCandidate,
        *,
        food: str = "",
        potion: str = "",
        active_buffs: tuple[str, ...] = (),
    ) -> tuple[float, dict[str, Any], tuple[str, ...]]:
        best_value: float | None = None
        best_payload: dict[str, Any] | None = None
        best_unresolved: tuple[str, ...] = ()
        best_state: tuple[str, str] | None = None
        states = self.mundus_states(objective_key)

        for primary, secondary in states:
            kwargs: dict[str, Any] = {"mundus": primary}
            if self.second_mundus_setter is None:
                kwargs["second_mundus"] = secondary
            if str(food or "").strip():
                kwargs["food"] = food
            if str(potion or "").strip():
                kwargs["potion"] = potion
            if tuple(active_buffs or ()):
                kwargs["active_buffs"] = tuple(active_buffs)

            if self.second_mundus_setter is not None:
                self.second_mundus_setter(secondary)
            try:
                value, payload, unresolved = self.evaluator.evaluate_candidate(
                    objective_key,
                    candidate,
                    **kwargs,
                )
            finally:
                if self.second_mundus_setter is not None:
                    self.second_mundus_setter("")

            score = float(value)
            state_key = (primary.casefold(), secondary.casefold())
            if (
                best_value is None
                or score > best_value + 1e-9
                or (
                    abs(score - best_value) <= 1e-9
                    and (best_state is None or state_key < best_state)
                )
            ):
                best_value = score
                best_payload = dict(payload)
                best_unresolved = tuple(unresolved or ())
                best_state = state_key

        if best_value is None or best_payload is None:
            raise ValueError("Twice-Born Star Mundus search produced no legal candidate")

        best_payload["twice_born_mundus_states_scored"] = len(states)
        return best_value, best_payload, best_unresolved


__all__ = ["ExtremeTwiceBornMundusStructuralStatEvaluator"]
