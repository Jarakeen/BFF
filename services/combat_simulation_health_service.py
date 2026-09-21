from __future__ import annotations

"""Project explicit recipient-bound healing into deterministic health changes."""

from dataclasses import dataclass
from math import isfinite

from models.combat_simulation import (
    CombatSimulationEvent,
    CombatSimulationTargetState,
    SimulationEventPriority,
)
from services.combat_simulation_health_ordering_service import (
    CombatSimulationHealthOrderingService,
)


@dataclass(frozen=True)
class CombatSimulationHealthProjection:
    events: tuple[CombatSimulationEvent, ...]
    unresolved: tuple[str, ...] = ()
    damage_unresolved: tuple[str, ...] = ()


class CombatSimulationHealthService:
    """Apply bound healing/damage events to explicit combatant Health state."""

    _HEAL_EVENT_TYPES = frozenset({"direct_heal", "periodic_heal"})
    _DAMAGE_EVENT_TYPES = frozenset({"incoming_damage", "outgoing_damage"})

    def __init__(
        self,
        *,
        ordering_service: CombatSimulationHealthOrderingService | None = None,
    ) -> None:
        self.ordering_service = ordering_service or CombatSimulationHealthOrderingService()

    def _coalesce_same_source_damage(
        self,
        events: tuple[CombatSimulationEvent, ...],
    ) -> tuple[CombatSimulationEvent, ...]:
        grouped: dict[
            tuple[str, float, int, int, str, str],
            list[CombatSimulationEvent],
        ] = {}
        passthrough: list[CombatSimulationEvent] = []

        for event in events:
            if event.event_type not in self._DAMAGE_EVENT_TYPES:
                passthrough.append(event)
                continue
            payload = event.payload_dict()
            recipient = str(payload.get("recipient") or "").strip()
            key = (
                recipient,
                float(event.time_seconds),
                int(event.priority),
                int(event.sequence),
                str(event.event_type),
                str(event.source or "").strip(),
            )
            grouped.setdefault(key, []).append(event)

        combined: list[CombatSimulationEvent] = list(passthrough)
        for key, rows in grouped.items():
            if len(rows) == 1:
                combined.append(rows[0])
                continue

            amounts = [row.payload_dict().get("amount") for row in rows]
            if any(amount is None for amount in amounts):
                combined.extend(rows)
                continue
            try:
                numeric = [float(amount) for amount in amounts]
            except (TypeError, ValueError):
                combined.extend(rows)
                continue
            if any(not isfinite(amount) for amount in numeric):
                combined.extend(rows)
                continue

            recipient, time_seconds, priority, sequence, event_type, source = key
            damage_types = tuple(
                dict.fromkeys(
                    str(row.payload_dict().get("damage_type") or "").strip()
                    for row in rows
                    if str(row.payload_dict().get("damage_type") or "").strip()
                )
            )
            combined.append(
                CombatSimulationEvent(
                    time_seconds=time_seconds,
                    priority=priority,
                    sequence=sequence,
                    event_type=event_type,
                    source=source,
                    payload=(
                        ("recipient", recipient),
                        ("amount", sum(numeric)),
                        (
                            "damage_type",
                            damage_types[0] if len(damage_types) == 1 else "mixed",
                        ),
                        ("component_count", len(rows)),
                    ),
                )
            )

        return tuple(
            sorted(
                combined,
                key=lambda event: (
                    event.time_seconds,
                    event.priority,
                    event.sequence,
                    event.event_type,
                    event.source.casefold(),
                ),
            )
        )

    def project(
        self,
        *,
        events: tuple[CombatSimulationEvent, ...],
        target_state: CombatSimulationTargetState | None,
    ) -> CombatSimulationHealthProjection:
        if target_state is None:
            outgoing = tuple(
                event for event in events if event.event_type == "outgoing_damage"
            )
            damage_unresolved = tuple(
                dict.fromkeys(
                    f"{event.source} outgoing_damage at {event.time_seconds:g}s: "
                    "target Health state is required to prove applied damage"
                    for event in outgoing
                )
            )
            return CombatSimulationHealthProjection(
                events=(),
                unresolved=damage_unresolved,
                damage_unresolved=damage_unresolved,
            )

        health: dict[str, tuple[int | None, int | None]] = {
            item.identity: (item.current_health, item.maximum_health)
            for item in target_state.combatants
        }
        projected: list[CombatSimulationEvent] = []
        unresolved: list[str] = []
        damage_unresolved: list[str] = []

        def add_unresolved(message: str, *, damage_blocking: bool = False) -> None:
            unresolved.append(message)
            if damage_blocking:
                damage_unresolved.append(message)

        ordered = tuple(
            sorted(
                events,
                key=lambda event: (
                    event.time_seconds,
                    event.priority,
                    event.sequence,
                    event.event_type,
                    event.source.casefold(),
                ),
            )
        )
        collisions = self.ordering_service.collisions(ordered)
        ordered = self._coalesce_same_source_damage(ordered)
        blocked_from: dict[str, tuple[float, int, int]] = {}
        for item in collisions:
            point = (
                float(item.time_seconds),
                int(item.priority),
                int(item.sequence),
            )
            current = blocked_from.get(item.recipient)
            if current is None or point < current:
                blocked_from[item.recipient] = point
        unresolved.extend(item.message for item in collisions)
        damage_unresolved.extend(
            item.message
            for item in collisions
            if "outgoing_damage" in item.event_types
        )

        def is_blocked(
            recipient: str,
            event: CombatSimulationEvent,
        ) -> bool:
            boundary = blocked_from.get(recipient)
            if boundary is None:
                return False
            point = (
                float(event.time_seconds),
                int(event.priority),
                int(event.sequence),
            )
            return point >= boundary

        for event in ordered:
            payload = event.payload_dict()

            if event.event_type in self._DAMAGE_EVENT_TYPES:
                recipient = str(payload.get("recipient") or "").strip()
                if not recipient:
                    add_unresolved(
                        f"{event.source} {event.event_type} at {event.time_seconds:g}s: recipient is required",
                        damage_blocking=(event.event_type == "outgoing_damage"),
                    )
                    continue
                if is_blocked(recipient, event):
                    continue
                if recipient not in health:
                    add_unresolved(
                        f"{event.source} {event.event_type} at {event.time_seconds:g}s -> {recipient}: unknown combatant",
                        damage_blocking=(event.event_type == "outgoing_damage"),
                    )
                    continue
                current, maximum = health[recipient]
                if current is None or maximum is None:
                    add_unresolved(
                        f"{event.source} {event.event_type} at {event.time_seconds:g}s -> {recipient}: "
                        "current and maximum Health are required",
                        damage_blocking=(event.event_type == "outgoing_damage"),
                    )
                    continue
                if int(current) == 0:
                    add_unresolved(
                        f"{event.source} {event.event_type} at {event.time_seconds:g}s -> {recipient}: "
                        "recipient is dead; additional damage is not applied",
                        damage_blocking=(event.event_type == "outgoing_damage"),
                    )
                    continue
                amount = payload.get("amount")
                if amount is None:
                    add_unresolved(
                        f"{event.source} {event.event_type} at {event.time_seconds:g}s -> {recipient}: damage amount is unavailable",
                        damage_blocking=(event.event_type == "outgoing_damage"),
                    )
                    continue
                try:
                    attempted_damage = float(amount)
                except (TypeError, ValueError):
                    add_unresolved(
                        f"{event.source} {event.event_type} at {event.time_seconds:g}s -> {recipient}: damage amount must be numeric",
                        damage_blocking=(event.event_type == "outgoing_damage"),
                    )
                    continue
                if not isfinite(attempted_damage):
                    add_unresolved(
                        f"{event.source} {event.event_type} at {event.time_seconds:g}s -> {recipient}: damage amount must be finite",
                        damage_blocking=(event.event_type == "outgoing_damage"),
                    )
                    continue
                if attempted_damage < 0:
                    add_unresolved(
                        f"{event.source} {event.event_type} at {event.time_seconds:g}s -> {recipient}: damage amount cannot be negative",
                        damage_blocking=(event.event_type == "outgoing_damage"),
                    )
                    continue
                applied_damage = min(attempted_damage, float(current))
                overkill = max(0.0, attempted_damage - applied_damage)
                after = max(0, int(round(float(current) - applied_damage)))
                health[recipient] = (after, maximum)
                projected.append(
                    CombatSimulationEvent(
                        time_seconds=event.time_seconds,
                        priority=int(SimulationEventPriority.HEALTH_CHANGE),
                        sequence=event.sequence,
                        event_type="health_change",
                        source=event.source,
                        payload=(
                            ("recipient", recipient),
                            ("before", int(current)),
                            ("attempted_damage", attempted_damage),
                            ("applied_damage", applied_damage),
                            ("overkill", overkill),
                            ("after", int(after)),
                            ("maximum_health", int(maximum)),
                            ("origin_event_type", event.event_type),
                        ),
                    )
                )
                if int(current) > 0 and int(after) == 0:
                    projected.append(
                        CombatSimulationEvent(
                            time_seconds=event.time_seconds,
                            priority=int(SimulationEventPriority.EXPIRATION),
                            sequence=event.sequence,
                            event_type="death",
                            source=event.source,
                            payload=(
                                ("recipient", recipient),
                                ("overkill", overkill),
                                ("origin_event_type", event.event_type),
                            ),
                        )
                    )
                continue

            if event.event_type not in self._HEAL_EVENT_TYPES:
                continue
            recipients = payload.get("recipients")
            if not recipients:
                continue

            attempted = payload.get("modeled_heal")
            if attempted is None:
                unresolved.append(
                    f"{event.source} {event.event_type} at {event.time_seconds:g}s: modeled_heal is unavailable"
                )
                continue
            try:
                attempted_value = float(attempted)
            except (TypeError, ValueError):
                unresolved.append(
                    f"{event.source} {event.event_type} at {event.time_seconds:g}s: modeled_heal must be numeric"
                )
                continue
            if not isfinite(attempted_value):
                unresolved.append(
                    f"{event.source} {event.event_type} at {event.time_seconds:g}s: modeled_heal must be finite"
                )
                continue
            if attempted_value < 0:
                unresolved.append(
                    f"{event.source} {event.event_type} at {event.time_seconds:g}s: modeled_heal cannot be negative"
                )
                continue

            for recipient in tuple(recipients):
                recipient = str(recipient)
                if is_blocked(recipient, event):
                    continue
                current, maximum = health.get(recipient, (None, None))
                if current is None or maximum is None:
                    unresolved.append(
                        f"{event.source} {event.event_type} at {event.time_seconds:g}s -> {recipient}: "
                        "current and maximum Health are required"
                    )
                    continue

                if int(current) == 0:
                    unresolved.append(
                        f"{event.source} {event.event_type} at {event.time_seconds:g}s -> {recipient}: "
                        "recipient is dead; resurrection semantics are not modeled"
                    )
                    continue

                missing = max(0.0, float(maximum - current))
                applied = min(attempted_value, missing)
                overheal = max(0.0, attempted_value - applied)
                after = int(round(float(current) + applied))
                if after > maximum:
                    after = maximum
                health[str(recipient)] = (after, maximum)

                projected.append(
                    CombatSimulationEvent(
                        time_seconds=event.time_seconds,
                        priority=int(SimulationEventPriority.HEALTH_CHANGE),
                        sequence=event.sequence,
                        event_type="health_change",
                        source=event.source,
                        payload=(
                            ("recipient", str(recipient)),
                            ("before", int(current)),
                            ("attempted_heal", attempted_value),
                            ("applied_heal", applied),
                            ("overheal", overheal),
                            ("after", int(after)),
                            ("maximum_health", int(maximum)),
                            ("origin_event_type", event.event_type),
                        ),
                    )
                )

        return CombatSimulationHealthProjection(
            events=tuple(
                sorted(
                    projected,
                    key=lambda event: (
                        event.time_seconds,
                        event.priority,
                        event.sequence,
                        event.source.casefold(),
                        str(event.payload_dict().get("recipient") or "").casefold(),
                    ),
                )
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
            damage_unresolved=tuple(dict.fromkeys(damage_unresolved)),
        )


__all__ = [
    "CombatSimulationHealthProjection",
    "CombatSimulationHealthService",
]
