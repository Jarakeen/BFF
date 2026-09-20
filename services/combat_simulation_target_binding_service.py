from __future__ import annotations

"""Bind deterministic simulation events to explicit known recipients."""

from dataclasses import dataclass

from models.combat_simulation import (
    CombatSimulationEvent,
    CombatSimulationTargetState,
)


@dataclass(frozen=True)
class CombatSimulationTargetBindingProjection:
    events: tuple[CombatSimulationEvent, ...]
    unresolved: tuple[str, ...] = ()


class CombatSimulationTargetBindingService:
    """Attach explicit recipient identities without inventing geometry or selection."""

    _RECIPIENT_EVENT_TYPES = frozenset(
        {
            "direct_heal",
            "periodic_heal",
            "effect_apply",
        }
    )

    def bind(
        self,
        *,
        events: tuple[CombatSimulationEvent, ...],
        target_state: CombatSimulationTargetState | None,
    ) -> CombatSimulationTargetBindingProjection:
        if target_state is None:
            unresolved = self._missing_binding_messages(events)
            return CombatSimulationTargetBindingProjection(
                events=events,
                unresolved=unresolved,
            )

        combatants = {item.identity: item for item in target_state.combatants}
        bindings = {
            self._binding_key(
                time_seconds=item.time_seconds,
                sequence=item.sequence,
                event_type=item.event_type,
                source=item.source,
                coefficient_number=item.coefficient_number,
                effect_name=item.effect_name,
            ): item
            for item in target_state.recipient_bindings
        }

        unresolved: list[str] = []
        bound_events: list[CombatSimulationEvent] = []

        for event in events:
            if event.event_type not in self._RECIPIENT_EVENT_TYPES:
                bound_events.append(event)
                continue

            payload = event.payload_dict()
            coefficient_number = payload.get("coefficient_number")
            effect_name = payload.get("effect_name")
            key = self._binding_key(
                time_seconds=event.time_seconds,
                sequence=event.sequence,
                event_type=event.event_type,
                source=event.source,
                coefficient_number=(
                    None if coefficient_number is None else int(coefficient_number)
                ),
                effect_name=(
                    None if effect_name is None else str(effect_name)
                ),
            )
            binding = bindings.get(key)
            if binding is None:
                unresolved.append(self._missing_message(event))
                bound_events.append(event)
                continue

            unknown = tuple(
                identity
                for identity in binding.recipients
                if identity not in combatants
            )
            if unknown:
                unresolved.append(
                    self._label(event)
                    + ": recipient binding references unknown combatant(s): "
                    + ", ".join(unknown)
                )
                bound_events.append(event)
                continue

            invalid = tuple(
                identity
                for identity in binding.recipients
                if not self._recipient_allowed(
                    event=event,
                    payload=payload,
                    side=combatants[identity].side,
                )
            )
            if invalid:
                unresolved.append(
                    self._label(event)
                    + ": recipient binding conflicts with target scope: "
                    + ", ".join(invalid)
                )
                bound_events.append(event)
                continue

            bound_payload = tuple(event.payload) + (
                ("recipients", tuple(binding.recipients)),
            )
            bound_events.append(
                CombatSimulationEvent(
                    time_seconds=event.time_seconds,
                    priority=event.priority,
                    sequence=event.sequence,
                    event_type=event.event_type,
                    source=event.source,
                    payload=bound_payload,
                )
            )

        return CombatSimulationTargetBindingProjection(
            events=tuple(bound_events),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @classmethod
    def _missing_binding_messages(
        cls,
        events: tuple[CombatSimulationEvent, ...],
    ) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                cls._missing_message(event)
                for event in events
                if event.event_type in cls._RECIPIENT_EVENT_TYPES
            )
        )

    @staticmethod
    def _binding_key(
        *,
        time_seconds: float,
        sequence: int,
        event_type: str,
        source: str,
        coefficient_number: int | None,
        effect_name: str | None,
    ) -> tuple:
        return (
            float(time_seconds),
            int(sequence),
            str(event_type),
            str(source),
            coefficient_number,
            effect_name,
        )

    @classmethod
    def _missing_message(cls, event: CombatSimulationEvent) -> str:
        return cls._label(event) + ": explicit recipient binding is required"

    @staticmethod
    def _label(event: CombatSimulationEvent) -> str:
        return f"{event.source} {event.event_type} at {event.time_seconds:g}s"

    @staticmethod
    def _recipient_allowed(
        *,
        event: CombatSimulationEvent,
        payload: dict,
        side: str,
    ) -> bool:
        if event.event_type in {"direct_heal", "periodic_heal"}:
            return side in {"self", "ally"}

        target_scope = str(payload.get("target_scope") or "").strip().casefold()
        if target_scope == "self":
            return side == "self"
        if target_scope in {"ally", "self_or_ally", "group"}:
            return side in {"self", "ally"}
        if target_scope == "enemy":
            return side == "enemy"
        return False


__all__ = [
    "CombatSimulationTargetBindingProjection",
    "CombatSimulationTargetBindingService",
]
