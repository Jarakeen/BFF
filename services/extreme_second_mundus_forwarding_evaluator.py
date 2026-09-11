from __future__ import annotations

"""Forward a transient second Mundus into the canonical named-gear evaluator.

Some deeper Extreme scorer stacks wrap the named-gear evaluator with armor,
jewelry, active-bar, and runtime layers whose public signatures predate
``SecondMundus``. This tiny adapter lets the Twice-Born finite-axis enumerator set
the secondary boon explicitly while those wrappers continue forwarding the
primary Mundus through their established contract.
"""

from typing import Any

from services.extreme_named_gear_canonical_stat_evaluator import (
    ExtremeNamedGearCanonicalStatEvaluator,
)


class ExtremeSecondMundusForwardingEvaluator:
    """Preserve the wrapped evaluator contract while forwarding one second boon."""

    def __init__(self, evaluator: ExtremeNamedGearCanonicalStatEvaluator) -> None:
        self.evaluator = evaluator
        self.optimizer = evaluator.optimizer
        self.progression_service = evaluator.progression_service
        self._second_mundus = ""

    def set_second_mundus(self, value: str) -> None:
        self._second_mundus = str(value or "").strip()

    @property
    def second_mundus(self) -> str:
        return self._second_mundus

    def evaluate_candidate(
        self,
        objective_key: str,
        candidate: Any,
        *,
        mundus: str = "",
        food: str = "",
        potion: str = "",
        active_buffs: tuple[str, ...] = (),
    ):
        return self.evaluator.evaluate_candidate(
            objective_key,
            candidate,
            mundus=mundus,
            second_mundus=self._second_mundus,
            food=food,
            potion=potion,
            active_buffs=active_buffs,
        )


__all__ = ["ExtremeSecondMundusForwardingEvaluator"]
