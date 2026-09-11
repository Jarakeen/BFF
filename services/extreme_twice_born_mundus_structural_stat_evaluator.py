from __future__ import annotations

"""Finite Mundus search for an active Twice-Born Star 5-piece realization.

Ordinary builds keep the established one-Mundus evaluator. This adapter exists
only for a named gear witness whose active snapshot proves Twice-Born Star at five
pieces, and delegates every candidate back through canonical build evaluation.

The default path passes ``second_mundus`` directly to the wrapped evaluator. A
deeper composed evaluator may instead provide ``second_mundus_setter`` so the
secondary boon can be forwarded through an inner canonical named-gear evaluator
without duplicating the outer armor/runtime scoring stack.
"""

from collections.abc import Callable
from itertools import combinations
from typing import Any

from minmax.mundus_repository import MundusRepository
from services.extreme_structural_global_search_service import ExtremeStructuralCandidate


class ExtremeTwiceBornMundusStructuralStatEvaluator:
    """Score the legal zero/one/two-Mundus state space for Twice-Born Star."""

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

    def mundus_states(self) -> tuple[tuple[str, str], ...]:
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

        for primary, secondary in self.mundus_states():
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

        best_payload["twice_born_mundus_states_scored"] = len(self.mundus_states())
        return best_value, best_payload, best_unresolved


__all__ = ["ExtremeTwiceBornMundusStructuralStatEvaluator"]
