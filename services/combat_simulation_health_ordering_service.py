from __future__ import annotations

"""Detect unresolved same-instant Health consequence ordering."""

from dataclasses import dataclass

from models.combat_simulation import CombatSimulationEvent


_HEAL_EVENT_TYPES = frozenset({"direct_heal", "periodic_heal"})
_DAMAGE_EVENT_TYPES = frozenset({"incoming_damage", "outgoing_damage"})
_HEALTH_EVENT_TYPES = _HEAL_EVENT_TYPES | _DAMAGE_EVENT_TYPES


@dataclass(frozen=True)
class CombatSimulationHealthOrderingCollision:
    recipient: str
    time_seconds: float
    priority: int
    sequence: int
    event_types: tuple[str, ...]
    sources: tuple[str, ...]

    @property
    def message(self) -> str:
        return (
            f"{self.time_seconds:g}s #{self.sequence} -> {self.recipient}: "
            "Health consequence ordering is unresolved for same-instant events "
            f"[{', '.join(self.event_types)}] from [{', '.join(self.sources)}]"
        )


class CombatSimulationHealthOrderingService:
    """Find per-recipient Health events whose ordering is not proven.

    Events are considered safely ordered when timestamp, priority, or sequence differ.
    If two or more Health-changing consequences share all three coordinates for the
    same recipient, the simulator has no reviewed cross-source tie-break authority.
    """

    def collisions(
        self,
        events: tuple[CombatSimulationEvent, ...],
    ) -> tuple[CombatSimulationHealthOrderingCollision, ...]:
        grouped: dict[
            tuple[str, float, int, int],
            list[CombatSimulationEvent],
        ] = {}

        for event in events:
            if event.event_type not in _HEALTH_EVENT_TYPES:
                continue
            payload = event.payload_dict()
            recipients: tuple[str, ...]
            if event.event_type in _DAMAGE_EVENT_TYPES:
                recipient = str(payload.get("recipient") or "").strip()
                recipients = (recipient,) if recipient else ()
            else:
                recipients = tuple(
                    str(value or "").strip()
                    for value in tuple(payload.get("recipients") or ())
                    if str(value or "").strip()
                )

            for recipient in recipients:
                grouped.setdefault(
                    (
                        recipient,
                        float(event.time_seconds),
                        int(event.priority),
                        int(event.sequence),
                    ),
                    [],
                ).append(event)

        collisions: list[CombatSimulationHealthOrderingCollision] = []
        for (recipient, time_seconds, priority, sequence), rows in grouped.items():
            if len(rows) < 2:
                continue
            collisions.append(
                CombatSimulationHealthOrderingCollision(
                    recipient=recipient,
                    time_seconds=time_seconds,
                    priority=priority,
                    sequence=sequence,
                    event_types=tuple(
                        sorted({row.event_type for row in rows})
                    ),
                    sources=tuple(
                        sorted(
                            {str(row.source or "").strip() for row in rows},
                            key=str.casefold,
                        )
                    ),
                )
            )

        return tuple(
            sorted(
                collisions,
                key=lambda row: (
                    row.time_seconds,
                    row.priority,
                    row.sequence,
                    row.recipient.casefold(),
                ),
            )
        )


__all__ = [
    "CombatSimulationHealthOrderingCollision",
    "CombatSimulationHealthOrderingService",
]
