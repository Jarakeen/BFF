from __future__ import annotations

"""Project explicit recipient-bound healing into deterministic health changes."""

from dataclasses import dataclass

from models.combat_simulation import (
    CombatSimulationEvent,
    CombatSimulationTargetState,
    SimulationEventPriority,
)


@dataclass(frozen=True)
class CombatSimulationHealthProjection:
    events: tuple[CombatSimulationEvent, ...]
    unresolved: tuple[str, ...] = ()


class CombatSimulationHealthService:
    """Apply bound healing events to explicit combatant health state."""

    _HEAL_EVENT_TYPES = frozenset({"direct_heal", "periodic_heal"})
    _DAMAGE_EVENT_TYPES = frozenset({"incoming_damage", "outgoing_damage"})

    def project(
        self,
        *,
        events: tuple[CombatSimulationEvent, ...],
        target_state: CombatSimulationTargetState | None,
    ) -> CombatSimulationHealthProjection:
        if target_state is None:
            return CombatSimulationHealthProjection(events=(), unresolved=())

        health: dict[str, tuple[int | None, int | None]] = {
            item.identity: (item.current_health, item.maximum_health)
            for item in target_state.combatants
        }
        projected: list[CombatSimulationEvent] = []
        unresolved: list[str] = []

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

        for event in ordered:
            payload = event.payload_dict()

            if event.event_type in self._DAMAGE_EVENT_TYPES:
                recipient = str(payload.get("recipient") or "").strip()
                if not recipient:
                    unresolved.append(
                        f"{event.source} damage at {event.time_seconds:g}s: recipient is required"
                    )
                    continue
                if recipient not in health:
                    unresolved.append(
                        f"{event.source} damage at {event.time_seconds:g}s -> {recipient}: unknown combatant"
                    )
                    continue
                current, maximum = health[recipient]
                if current is None or maximum is None:
                    unresolved.append(
                        f"{event.source} damage at {event.time_seconds:g}s -> {recipient}: "
                        "current and maximum Health are required"
                    )
                    continue
                amount = payload.get("amount")
                if amount is None:
                    unresolved.append(
                        f"{event.source} damage at {event.time_seconds:g}s -> {recipient}: damage amount is unavailable"
                    )
                    continue
                attempted_damage = float(amount)
                if attempted_damage < 0:
                    unresolved.append(
                        f"{event.source} damage at {event.time_seconds:g}s -> {recipient}: damage amount cannot be negative"
                    )
                    continue
                applied_damage = min(attempted_damage, float(current))
                overkill = max(0.0, attempted_damage - applied_damage)
                after = max(0, int(round(float(current) - applied_damage)))
                health[recipient] = (after, maximum)
                projected.append(
                    CombatSimulationEvent(
                        time_seconds=event.time_seconds,
                        priority=int(SimulationEventPriority.DIRECT_RESULT),
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
            attempted_value = float(attempted)
            if attempted_value < 0:
                unresolved.append(
                    f"{event.source} {event.event_type} at {event.time_seconds:g}s: modeled_heal cannot be negative"
                )
                continue

            for recipient in tuple(recipients):
                current, maximum = health.get(str(recipient), (None, None))
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
                        priority=int(SimulationEventPriority.DIRECT_RESULT),
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
        )


__all__ = [
    "CombatSimulationHealthProjection",
    "CombatSimulationHealthService",
]
