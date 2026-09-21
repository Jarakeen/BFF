from __future__ import annotations

"""Deterministic replay verification for Combat Simulation."""

from dataclasses import dataclass
from typing import Callable

from models.combat_simulation import CombatSimulationResult


CombatSimulationRunner = Callable[[], CombatSimulationResult]


@dataclass(frozen=True)
class CombatSimulationReplayVerification:
    deterministic: bool
    first: CombatSimulationResult
    second: CombatSimulationResult
    differing_signature_fields: tuple[str, ...] = ()


class CombatSimulationDeterministicReplayService:
    """Run one deterministic simulation twice and compare canonical signatures."""

    _SIGNATURE_FIELDS = (
        "duration_seconds",
        "initial_bar",
        "final_bar",
        "events",
        "resources",
        "effect_windows",
        "target_state",
        "unresolved",
        "damage_unresolved",
    )

    def verify(
        self,
        runner: CombatSimulationRunner,
    ) -> CombatSimulationReplayVerification:
        if not callable(runner):
            raise TypeError("combat simulation replay verification requires a callable runner")

        first = runner()
        second = runner()
        if not isinstance(first, CombatSimulationResult) or not isinstance(
            second,
            CombatSimulationResult,
        ):
            raise TypeError(
                "combat simulation replay runner must return CombatSimulationResult"
            )

        first_signature = first.deterministic_signature
        second_signature = second.deterministic_signature
        differing = tuple(
            field
            for index, field in enumerate(self._SIGNATURE_FIELDS)
            if first_signature[index] != second_signature[index]
        )
        return CombatSimulationReplayVerification(
            deterministic=not differing,
            first=first,
            second=second,
            differing_signature_fields=differing,
        )


__all__ = [
    "CombatSimulationDeterministicReplayService",
    "CombatSimulationReplayVerification",
    "CombatSimulationRunner",
]
