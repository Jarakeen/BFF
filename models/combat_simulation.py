from __future__ import annotations

"""Phase 14 deterministic combat-simulation contracts.

These models deliberately consume the Phase 13 RotationPlan contract rather than
creating a competing action model. Consequence engines remain authoritative for
damage, healing, sustain, and proc semantics.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class SimulationEventPriority(IntEnum):
    ACTION = 10
    RESOURCE_COST = 20
    DIRECT_RESULT = 30
    TRIGGER = 40
    EFFECT_APPLY = 50
    RESOURCE_RESTORE = 60
    PERIODIC = 70
    EXPIRATION = 80
    SNAPSHOT = 90


@dataclass(frozen=True, order=True)
class CombatSimulationEvent:
    time_seconds: float
    priority: int
    sequence: int
    event_type: str
    source: str
    payload: tuple[tuple[str, Any], ...] = ()

    def payload_dict(self) -> dict[str, Any]:
        return dict(self.payload)


@dataclass(frozen=True)
class CombatSimulationResult:
    duration_seconds: float
    initial_bar: str
    final_bar: str
    events: tuple[CombatSimulationEvent, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def deterministic_signature(self) -> tuple:
        return (
            self.duration_seconds,
            self.initial_bar,
            self.final_bar,
            self.events,
            self.unresolved,
        )


__all__ = [
    "CombatSimulationEvent",
    "CombatSimulationResult",
    "SimulationEventPriority",
]
