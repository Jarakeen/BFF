from __future__ import annotations

"""Phase 14 deterministic combat-simulation contracts.

These models deliberately consume the Phase 13 RotationPlan contract rather than
creating a competing action model. Consequence engines remain authoritative for
damage, healing, sustain, and proc semantics.
"""

from dataclasses import dataclass
from enum import IntEnum
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

    def payload_dict(self) -> dict[str, Any]:
        return dict(self.payload)


@dataclass(frozen=True)
class CombatSimulationResourceResult:
    resource: str
    starting_amount: int
    ending_amount: int
    total_shortfall: int = 0


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
        if self.time_seconds < 0:
            raise ValueError("incoming damage time cannot be negative")
        if self.sequence < 0:
            raise ValueError("incoming damage sequence cannot be negative")
        if not str(self.source or "").strip():
            raise ValueError("incoming damage source is required")
        if not str(self.recipient or "").strip():
            raise ValueError("incoming damage recipient is required")
        if float(self.amount) < 0:
            raise ValueError("incoming damage amount cannot be negative")
        object.__setattr__(self, "source", str(self.source).strip())
        object.__setattr__(self, "recipient", str(self.recipient).strip())
        object.__setattr__(self, "amount", float(self.amount))
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
        if self.time_seconds < 0:
            raise ValueError("outgoing damage time cannot be negative")
        if self.sequence < 0:
            raise ValueError("outgoing damage sequence cannot be negative")
        if not str(self.source or "").strip():
            raise ValueError("outgoing damage source is required")
        if not str(self.recipient or "").strip():
            raise ValueError("outgoing damage recipient is required")
        if float(self.amount) < 0:
            raise ValueError("outgoing damage amount cannot be negative")
        object.__setattr__(self, "source", str(self.source).strip())
        object.__setattr__(self, "recipient", str(self.recipient).strip())
        object.__setattr__(self, "amount", float(self.amount))
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
        if self.time_seconds < 0:
            raise ValueError("recipient binding time cannot be negative")
        if self.sequence < 0:
            raise ValueError("recipient binding sequence cannot be negative")
        if not str(self.event_type or "").strip():
            raise ValueError("recipient binding event_type is required")
        if not str(self.source or "").strip():
            raise ValueError("recipient binding source is required")
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
