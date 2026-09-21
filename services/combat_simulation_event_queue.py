from __future__ import annotations

"""Stable priority queue for Phase 14 combat simulation."""

from heapq import heappop, heappush
from itertools import count

from models.combat_simulation import CombatSimulationEvent


class CombatSimulationEventQueue:
    """Order events by explicit simulation coordinates, never by payload values."""

    def __init__(self) -> None:
        self._heap: list[tuple[tuple, int, CombatSimulationEvent]] = []
        self._counter = count()

    @staticmethod
    def _key(event: CombatSimulationEvent) -> tuple:
        return (
            float(event.time_seconds),
            int(event.priority),
            int(event.sequence),
            str(event.event_type),
            str(event.source or "").casefold(),
        )

    def push(self, event: CombatSimulationEvent) -> None:
        if not isinstance(event, CombatSimulationEvent):
            raise TypeError("combat simulation queue requires CombatSimulationEvent")
        insertion = next(self._counter)
        heappush(
            self._heap,
            (self._key(event), insertion, event),
        )

    def extend(self, events) -> None:
        for event in events:
            self.push(event)

    def pop(self) -> CombatSimulationEvent:
        if not self._heap:
            raise IndexError("pop from empty combat simulation queue")
        _key, _insertion, event = heappop(self._heap)
        return event

    def __bool__(self) -> bool:
        return bool(self._heap)

    def __len__(self) -> int:
        return len(self._heap)


__all__ = ["CombatSimulationEventQueue"]
