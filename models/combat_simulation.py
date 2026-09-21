from __future__ import annotations

"""Phase 14 deterministic combat-simulation contracts.

These models deliberately consume the Phase 13 RotationPlan contract rather than
creating a competing action model. Consequence engines remain authoritative for
damage, healing, sustain, and proc semantics.
"""

from dataclasses import dataclass
from enum import IntEnum
from math import isfinite
from typing import Any

from minmax.runtime_effect_window import RuntimeEffectActiveWindow


class SimulationEventPriority(IntEnum):
    ACTION = 10
    RESOURCE_COST = 20
    DIRECT_RESULT = 30
    HEALTH_CHANGE = 35
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

    def __post_init__(self) -> None:
        time_seconds = float(self.time_seconds)
        if not isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("combat simulation event time must be finite and non-negative")
        sequence = int(self.sequence)
        if sequence < 0:
            raise ValueError("combat simulation event sequence cannot be negative")
        event_type = str(self.event_type or "").strip()
        if not event_type:
            raise ValueError("combat simulation event_type is required")
        source = str(self.source or "").strip()
        if not source:
            raise ValueError("combat simulation event source is required")
        object.__setattr__(self, "time_seconds", time_seconds)
        object.__setattr__(self, "priority", int(self.priority))
        object.__setattr__(self, "sequence", sequence)
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "source", source)

    def payload_dict(self) -> dict[str, Any]:
        return dict(self.payload)


@dataclass(frozen=True)
class CombatSimulationResourceResult:
    resource: str
    starting_amount: int
    ending_amount: int
    total_shortfall: int = 0

    def __post_init__(self) -> None:
        resource = str(self.resource or "").strip().casefold()
        if not resource:
            raise ValueError("combat simulation resource identity is required")
        starting_amount = int(self.starting_amount)
        ending_amount = int(self.ending_amount)
        total_shortfall = int(self.total_shortfall)
        if starting_amount < 0 or ending_amount < 0:
            raise ValueError("combat simulation resource amounts cannot be negative")
        if total_shortfall < 0:
            raise ValueError("combat simulation resource shortfall cannot be negative")
        object.__setattr__(self, "resource", resource)
        object.__setattr__(self, "starting_amount", starting_amount)
        object.__setattr__(self, "ending_amount", ending_amount)
        object.__setattr__(self, "total_shortfall", total_shortfall)


@dataclass(frozen=True)
class CombatSimulationCombatant:
    identity: str
    side: str = "ally"
    current_health: int | None = None
    maximum_health: int | None = None

    def __post_init__(self) -> None:
        identity = str(self.identity or "").strip()
        if not identity:
            raise ValueError("simulation combatant identity is required")
        side = str(self.side or "").strip().casefold()
        if side not in {"self", "ally", "enemy"}:
            raise ValueError("simulation combatant side must be self, ally, or enemy")
        if self.current_health is not None and int(self.current_health) < 0:
            raise ValueError("simulation combatant current_health cannot be negative")
        if self.maximum_health is not None and int(self.maximum_health) <= 0:
            raise ValueError("simulation combatant maximum_health must be positive")
        if (
            self.current_health is not None
            and self.maximum_health is not None
            and int(self.current_health) > int(self.maximum_health)
        ):
            raise ValueError("simulation combatant current_health cannot exceed maximum_health")
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "side", side)
        if self.current_health is not None:
            object.__setattr__(self, "current_health", int(self.current_health))
        if self.maximum_health is not None:
            object.__setattr__(self, "maximum_health", int(self.maximum_health))


@dataclass(frozen=True)
class CombatSimulationIncomingDamage:
    time_seconds: float
    sequence: int
    source: str
    recipient: str
    amount: float
    damage_type: str | None = None

    def __post_init__(self) -> None:
        time_seconds = float(self.time_seconds)
        amount = float(self.amount)
        if not isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("incoming damage time must be finite and non-negative")
        if self.sequence < 0:
            raise ValueError("incoming damage sequence cannot be negative")
        if not str(self.source or "").strip():
            raise ValueError("incoming damage source is required")
        if not str(self.recipient or "").strip():
            raise ValueError("incoming damage recipient is required")
        if not isfinite(amount) or amount < 0:
            raise ValueError("incoming damage amount must be finite and non-negative")
        object.__setattr__(self, "time_seconds", time_seconds)
        object.__setattr__(self, "source", str(self.source).strip())
        object.__setattr__(self, "recipient", str(self.recipient).strip())
        object.__setattr__(self, "amount", amount)
        if self.damage_type is not None:
            object.__setattr__(self, "damage_type", str(self.damage_type).strip() or None)


@dataclass(frozen=True)
class CombatSimulationOutgoingDamage:
    """Explicit already-resolved player/group damage applied to one combatant.

    The simulator does not calculate mitigation here. Callers must provide the
    final damage amount after the authoritative damage engine has resolved its
    mechanics.
    """

    time_seconds: float
    sequence: int
    source: str
    recipient: str
    amount: float
    damage_type: str | None = None

    def __post_init__(self) -> None:
        time_seconds = float(self.time_seconds)
        amount = float(self.amount)
        if not isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("outgoing damage time must be finite and non-negative")
        if self.sequence < 0:
            raise ValueError("outgoing damage sequence cannot be negative")
        if not str(self.source or "").strip():
            raise ValueError("outgoing damage source is required")
        if not str(self.recipient or "").strip():
            raise ValueError("outgoing damage recipient is required")
        if not isfinite(amount) or amount < 0:
            raise ValueError("outgoing damage amount must be finite and non-negative")
        object.__setattr__(self, "time_seconds", time_seconds)
        object.__setattr__(self, "source", str(self.source).strip())
        object.__setattr__(self, "recipient", str(self.recipient).strip())
        object.__setattr__(self, "amount", amount)
        if self.damage_type is not None:
            object.__setattr__(self, "damage_type", str(self.damage_type).strip() or None)


@dataclass(frozen=True)
class CombatSimulationRecipientBinding:
    time_seconds: float
    sequence: int
    event_type: str
    source: str
    recipients: tuple[str, ...]
    coefficient_number: int | None = None
    effect_name: str | None = None

    def __post_init__(self) -> None:
        time_seconds = float(self.time_seconds)
        if not isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("recipient binding time must be finite and non-negative")
        if self.sequence < 0:
            raise ValueError("recipient binding sequence cannot be negative")
        if not str(self.event_type or "").strip():
            raise ValueError("recipient binding event_type is required")
        if not str(self.source or "").strip():
            raise ValueError("recipient binding source is required")
        object.__setattr__(self, "time_seconds", time_seconds)
        object.__setattr__(self, "sequence", int(self.sequence))
        recipients = tuple(str(value or "").strip() for value in self.recipients)
        if any(not value for value in recipients):
            raise ValueError("recipient binding identities must be non-empty")
        if len(set(recipients)) != len(recipients):
            raise ValueError("recipient binding identities must be unique")
        object.__setattr__(self, "recipients", recipients)


@dataclass(frozen=True)
class CombatSimulationTargetState:
    combatants: tuple[CombatSimulationCombatant, ...]
    recipient_bindings: tuple[CombatSimulationRecipientBinding, ...] = ()

    def __post_init__(self) -> None:
        identities = tuple(item.identity for item in self.combatants)
        if len(set(identities)) != len(identities):
            raise ValueError("simulation combatant identities must be unique")

        binding_keys = tuple(
            (
                float(item.time_seconds),
                int(item.sequence),
                str(item.event_type),
                str(item.source),
                item.coefficient_number,
                item.effect_name,
            )
            for item in self.recipient_bindings
        )
        if len(set(binding_keys)) != len(binding_keys):
            raise ValueError("simulation recipient binding identities must be unique")

    def combatant(self, identity: str) -> CombatSimulationCombatant | None:
        wanted = str(identity or "").strip()
        return next((item for item in self.combatants if item.identity == wanted), None)


@dataclass(frozen=True)
class CombatSimulationHealthSnapshot:
    identity: str
    current_health: int | None
    maximum_health: int | None
    is_dead: bool = False


@dataclass(frozen=True)
class CombatSimulationResourceSnapshot:
    resource: str
    current_amount: int


@dataclass(frozen=True)
class CombatSimulationSnapshot:
    time_seconds: float
    active_bar: str
    resources: tuple[CombatSimulationResourceSnapshot, ...]
    health: tuple[CombatSimulationHealthSnapshot, ...] = ()
    active_effect_windows: tuple[RuntimeEffectActiveWindow, ...] = ()
    target_state: CombatSimulationTargetState | None = None
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class CombatSimulationResult:
    duration_seconds: float
    initial_bar: str
    final_bar: str
    events: tuple[CombatSimulationEvent, ...]
    resources: tuple[CombatSimulationResourceResult, ...] = ()
    effect_windows: tuple[RuntimeEffectActiveWindow, ...] = ()
    target_state: CombatSimulationTargetState | None = None
    unresolved: tuple[str, ...] = ()
    damage_unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        duration_seconds = float(self.duration_seconds)
        if not isfinite(duration_seconds) or duration_seconds < 0:
            raise ValueError(
                "combat simulation result duration must be finite and non-negative"
            )
        if any(float(event.time_seconds) > duration_seconds for event in self.events):
            raise ValueError(
                "combat simulation result cannot contain events beyond its duration"
            )
        event_keys = tuple(
            (
                float(event.time_seconds),
                int(event.priority),
                int(event.sequence),
                str(event.event_type),
                str(event.source).casefold(),
            )
            for event in self.events
        )
        if event_keys != tuple(sorted(event_keys)):
            raise ValueError(
                "combat simulation result events must be in canonical timeline order"
            )
        resource_keys = tuple(item.resource for item in self.resources)
        if len(set(resource_keys)) != len(resource_keys):
            raise ValueError(
                "combat simulation result resource identities must be unique"
            )
        resource_event_types = {
            "action_cost",
            "recovery_tick",
            "restoration",
            "resource_maximum",
        }
        event_resource_keys = {
            str(event.payload_dict().get("resource") or "").strip().casefold()
            for event in self.events
            if event.event_type in resource_event_types
        }
        if "" in event_resource_keys:
            raise ValueError(
                "combat simulation resource events require resource identity"
            )
        undeclared_resources = event_resource_keys.difference(resource_keys)
        if undeclared_resources:
            raise ValueError(
                "combat simulation resource events require matching resource summaries"
            )
        summaries_by_resource = {item.resource: item for item in self.resources}
        for resource_key in event_resource_keys:
            rows = [
                event
                for event in self.events
                if event.event_type in resource_event_types
                and str(event.payload_dict().get("resource") or "").strip().casefold()
                == resource_key
            ]
            if not rows:
                continue
            first_payload = rows[0].payload_dict()
            last_payload = rows[-1].payload_dict()
            if "before" not in first_payload or "after" not in last_payload:
                raise ValueError(
                    "combat simulation resource events require before/after state"
                )
            summary = summaries_by_resource[resource_key]
            if int(first_payload["before"]) != int(summary.starting_amount):
                raise ValueError(
                    "combat simulation resource summary start does not match event state"
                )
            if int(last_payload["after"]) != int(summary.ending_amount):
                raise ValueError(
                    "combat simulation resource summary end does not match event state"
                )
        health_rows = [
            event
            for event in self.events
            if event.event_type == "health_change"
        ]
        if health_rows and self.target_state is None:
            raise ValueError(
                "combat simulation health changes require target state"
            )
        if self.target_state is not None:
            health_by_recipient: dict[str, int | None] = {
                item.identity: item.current_health
                for item in self.target_state.combatants
            }
            maximum_by_recipient: dict[str, int | None] = {
                item.identity: item.maximum_health
                for item in self.target_state.combatants
            }
            for event in health_rows:
                payload = event.payload_dict()
                recipient = str(payload.get("recipient") or "").strip()
                if not recipient:
                    raise ValueError(
                        "combat simulation health change requires recipient identity"
                    )
                if recipient not in health_by_recipient:
                    raise ValueError(
                        "combat simulation health change recipient is not present in target state"
                    )
                if "before" not in payload or "after" not in payload:
                    raise ValueError(
                        "combat simulation health changes require before/after state"
                    )
                expected_before = health_by_recipient[recipient]
                if expected_before is None:
                    raise ValueError(
                        "combat simulation health change requires known starting Health"
                    )
                before = int(payload["before"])
                after = int(payload["after"])
                if before != int(expected_before):
                    raise ValueError(
                        "combat simulation health change before/after chain is inconsistent"
                    )
                maximum = maximum_by_recipient[recipient]
                if after < 0 or (maximum is not None and after > int(maximum)):
                    raise ValueError(
                        "combat simulation health change after state is outside valid Health bounds"
                    )
                if (
                    "maximum_health" in payload
                    and maximum is not None
                    and int(payload["maximum_health"]) != int(maximum)
                ):
                    raise ValueError(
                        "combat simulation health change maximum does not match target state"
                    )
                health_by_recipient[recipient] = after
        initial_bar = str(self.initial_bar or "").strip().casefold()
        final_bar = str(self.final_bar or "").strip().casefold()
        if initial_bar not in {"front", "back"} or final_bar not in {"front", "back"}:
            raise ValueError(
                "combat simulation result bars must be front or back"
            )
        object.__setattr__(self, "duration_seconds", duration_seconds)
        object.__setattr__(self, "initial_bar", initial_bar)
        object.__setattr__(self, "final_bar", final_bar)

    @property
    def deterministic_signature(self) -> tuple:
        return (
            self.duration_seconds,
            self.initial_bar,
            self.final_bar,
            self.events,
            self.resources,
            self.effect_windows,
            self.target_state,
            self.unresolved,
            self.damage_unresolved,
        )


__all__ = [
    "CombatSimulationEvent",
    "CombatSimulationCombatant",
    "CombatSimulationIncomingDamage",
    "CombatSimulationOutgoingDamage",
    "CombatSimulationRecipientBinding",
    "CombatSimulationTargetState",
    "CombatSimulationResourceResult",
    "CombatSimulationHealthSnapshot",
    "CombatSimulationResourceSnapshot",
    "CombatSimulationSnapshot",
    "CombatSimulationResult",
    "SimulationEventPriority",
]
