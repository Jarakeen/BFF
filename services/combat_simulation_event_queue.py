from __future__ import annotations

"""Stable priority queue for Phase 14 combat simulation."""

from heapq import heappop, heappush

from models.combat_simulation import CombatSimulationEvent


class CombatSimulationEventQueue:
    """Order events by timestamp, explicit priority, then deterministic sequence."""

    def __init__(self) -> None:
        self._heap: list[CombatSimulationEvent] = []

    def push(self, event: CombatSimulationEvent) -> None:
        if not isinstance(event, CombatSimulationEvent):
            raise TypeError("combat simulation queue requires CombatSimulationEvent")
        heappush(self._heap, event)

    def extend(self, events) -> None:
        for event in events:
            self.push(event)

    def pop(self) -> CombatSimulationEvent:
        if not self._heap:
            raise IndexError("pop from empty combat simulation queue")
        return heappop(self._heap)

    def __bool__(self) -> bool:
        return bool(self._heap)

    def __len__(self) -> int:
        return len(self._heap)


__all__ = ["CombatSimulationEventQueue"]
