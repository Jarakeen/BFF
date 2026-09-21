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
    RESOURCE_MAXIMUM = 15
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
        priority = int(self.priority)
        if priority < 0:
            raise ValueError("combat simulation event priority cannot be negative")
        payload = tuple(self.payload)
        payload_keys: list[str] = []
        normalized_payload: list[tuple[str, Any]] = []
        for item in payload:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError("combat simulation event payload entries must be key/value pairs")
            key = str(item[0] or "").strip()
            if not key:
                raise ValueError("combat simulation event payload keys must be non-empty")
            payload_keys.append(key)
            normalized_payload.append((key, item[1]))
        if len(set(payload_keys)) != len(payload_keys):
            raise ValueError("combat simulation event payload keys must be unique")
        object.__setattr__(self, "time_seconds", time_seconds)
        object.__setattr__(self, "priority", priority)
        object.__setattr__(self, "sequence", sequence)
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "payload", tuple(normalized_payload))

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
        sequence = int(self.sequence)
        if not isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("incoming damage time must be finite and non-negative")
        if sequence < 0:
            raise ValueError("incoming damage sequence cannot be negative")
        if not str(self.source or "").strip():
            raise ValueError("incoming damage source is required")
        if not str(self.recipient or "").strip():
            raise ValueError("incoming damage recipient is required")
        if not isfinite(amount) or amount < 0:
            raise ValueError("incoming damage amount must be finite and non-negative")
        object.__setattr__(self, "time_seconds", time_seconds)
        object.__setattr__(self, "sequence", sequence)
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
        sequence = int(self.sequence)
        if not isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("outgoing damage time must be finite and non-negative")
        if sequence < 0:
            raise ValueError("outgoing damage sequence cannot be negative")
        if not str(self.source or "").strip():
            raise ValueError("outgoing damage source is required")
        if not str(self.recipient or "").strip():
            raise ValueError("outgoing damage recipient is required")
        if not isfinite(amount) or amount < 0:
            raise ValueError("outgoing damage amount must be finite and non-negative")
        object.__setattr__(self, "time_seconds", time_seconds)
        object.__setattr__(self, "sequence", sequence)
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
        event_type = str(self.event_type or "").strip()
        source = str(self.source or "").strip()
        if not event_type:
            raise ValueError("recipient binding event_type is required")
        if not source:
            raise ValueError("recipient binding source is required")
        object.__setattr__(self, "time_seconds", time_seconds)
        object.__setattr__(self, "sequence", int(self.sequence))
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "source", source)
        if self.coefficient_number is not None:
            object.__setattr__(self, "coefficient_number", int(self.coefficient_number))
        if self.effect_name is not None:
            object.__setattr__(
                self,
                "effect_name",
                str(self.effect_name).strip() or None,
            )
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
        object.__setattr__(
            self,
            "recipient_bindings",
            tuple(
                sorted(
                    self.recipient_bindings,
                    key=lambda item: (
                        float(item.time_seconds),
                        int(item.sequence),
                        str(item.event_type),
                        str(item.source).casefold(),
                        -1 if item.coefficient_number is None else int(item.coefficient_number),
                        str(item.effect_name or ""),
                        tuple(item.recipients),
                    ),
                )
            ),
        )

    def combatant(self, identity: str) -> CombatSimulationCombatant | None:
        wanted = str(identity or "").strip()
        return next((item for item in self.combatants if item.identity == wanted), None)


@dataclass(frozen=True)
class CombatSimulationHealthSnapshot:
    identity: str
    current_health: int | None
    maximum_health: int | None
    is_dead: bool = False

    def __post_init__(self) -> None:
        identity = str(self.identity or "").strip()
        if not identity:
            raise ValueError("combat simulation Health snapshot identity is required")
        current = None if self.current_health is None else int(self.current_health)
        maximum = None if self.maximum_health is None else int(self.maximum_health)
        if current is not None and current < 0:
            raise ValueError("combat simulation Health snapshot current Health cannot be negative")
        if maximum is not None and maximum <= 0:
            raise ValueError("combat simulation Health snapshot maximum Health must be positive")
        if current is not None and maximum is not None and current > maximum:
            raise ValueError("combat simulation Health snapshot current Health cannot exceed maximum")
        is_dead = bool(self.is_dead)
        if is_dead and current != 0:
            raise ValueError("combat simulation Health snapshot dead state requires zero Health")
        if current == 0 and not is_dead:
            raise ValueError("combat simulation Health snapshot zero Health requires dead state")
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "current_health", current)
        object.__setattr__(self, "maximum_health", maximum)
        object.__setattr__(self, "is_dead", is_dead)


@dataclass(frozen=True)
class CombatSimulationResourceSnapshot:
    resource: str
    current_amount: int

    def __post_init__(self) -> None:
        resource = str(self.resource or "").strip().casefold()
        if not resource:
            raise ValueError("combat simulation resource snapshot identity is required")
        current_amount = int(self.current_amount)
        if current_amount < 0:
            raise ValueError("combat simulation resource snapshot amount cannot be negative")
        object.__setattr__(self, "resource", resource)
        object.__setattr__(self, "current_amount", current_amount)


@dataclass(frozen=True)
class CombatSimulationSnapshot:
    time_seconds: float
    active_bar: str
    resources: tuple[CombatSimulationResourceSnapshot, ...]
    health: tuple[CombatSimulationHealthSnapshot, ...] = ()
    active_effect_windows: tuple[RuntimeEffectActiveWindow, ...] = ()
    target_state: CombatSimulationTargetState | None = None
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        time_seconds = float(self.time_seconds)
        if not isfinite(time_seconds) or time_seconds < 0:
            raise ValueError("combat simulation snapshot time must be finite and non-negative")
        active_bar = str(self.active_bar or "").strip().casefold()
        if active_bar not in {"front", "back"}:
            raise ValueError("combat simulation snapshot active bar must be front or back")
        resource_keys = tuple(item.resource for item in self.resources)
        if len(set(resource_keys)) != len(resource_keys):
            raise ValueError("combat simulation snapshot resource identities must be unique")
        health_keys = tuple(item.identity for item in self.health)
        if len(set(health_keys)) != len(health_keys):
            raise ValueError("combat simulation snapshot Health identities must be unique")
        if self.target_state is not None:
            target_by_identity = {
                item.identity: item
                for item in self.target_state.combatants
            }
            for item in self.health:
                if item.identity not in target_by_identity:
                    raise ValueError(
                        "combat simulation snapshot Health identity is not present in target state"
                    )
                target = target_by_identity[item.identity]
                if (
                    item.maximum_health is not None
                    and target.maximum_health is not None
                    and int(item.maximum_health) != int(target.maximum_health)
                ):
                    raise ValueError(
                        "combat simulation snapshot maximum Health does not match target state"
                    )
        object.__setattr__(self, "time_seconds", time_seconds)
        object.__setattr__(self, "active_bar", active_bar)


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
        if (
            self.target_state is not None
            and any(
                float(binding.time_seconds) > duration_seconds
                for binding in self.target_state.recipient_bindings
            )
        ):
            raise ValueError(
                "combat simulation recipient binding cannot occur beyond result duration"
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
        for resource_key, summary in summaries_by_resource.items():
            if resource_key in event_resource_keys:
                continue
            if int(summary.starting_amount) != int(summary.ending_amount):
                raise ValueError(
                    "combat simulation resource summary cannot change without event evidence"
                )
            if int(summary.total_shortfall) != 0:
                raise ValueError(
                    "combat simulation resource summary cannot record shortfall without event evidence"
                )
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
            summary = summaries_by_resource[resource_key]
            expected_before = int(summary.starting_amount)
            calculated_shortfall = 0
            for row in rows:
                payload = row.payload_dict()
                if "before" not in payload or "after" not in payload:
                    raise ValueError(
                        "combat simulation resource events require before/after state"
                    )
                before = int(payload["before"])
                after = int(payload["after"])
                if before != expected_before:
                    raise ValueError(
                        "combat simulation resource event before/after chain is inconsistent"
                    )
                if before < 0 or after < 0:
                    raise ValueError(
                        "combat simulation resource event state cannot be negative"
                    )
                if "applied_change" in payload:
                    applied_change = int(payload["applied_change"])
                    if before + applied_change != after:
                        raise ValueError(
                            "combat simulation resource event arithmetic is inconsistent"
                        )
                    attempted_change = int(payload.get("attempted_change", applied_change))
                    shortfall = int(payload.get("shortfall", 0))
                    wasted_restore = int(payload.get("wasted_restore", 0))
                    calculated_shortfall += shortfall
                    if shortfall < 0 or wasted_restore < 0:
                        raise ValueError(
                            "combat simulation resource shortfall and wasted restore cannot be negative"
                        )
                    if row.event_type == "action_cost":
                        if attempted_change > 0 or applied_change > 0:
                            raise ValueError(
                                "combat simulation action cost changes must be non-positive"
                            )
                        if wasted_restore != 0:
                            raise ValueError(
                                "combat simulation action cost cannot record wasted restore"
                            )
                        if shortfall != abs(attempted_change) - abs(applied_change):
                            raise ValueError(
                                "combat simulation action cost shortfall arithmetic is inconsistent"
                            )
                    elif row.event_type in {"recovery_tick", "restoration"}:
                        if attempted_change < 0 or applied_change < 0:
                            raise ValueError(
                                "combat simulation resource restore changes must be non-negative"
                            )
                        if shortfall != 0:
                            raise ValueError(
                                "combat simulation resource restore cannot record action-cost shortfall"
                            )
                        if wasted_restore != attempted_change - applied_change:
                            raise ValueError(
                                "combat simulation wasted restore arithmetic is inconsistent"
                            )
                    elif row.event_type == "resource_maximum":
                        if attempted_change != 0 or shortfall != 0 or wasted_restore != 0:
                            raise ValueError(
                                "combat simulation resource maximum carries invalid delta evidence"
                            )
                expected_before = after
            if expected_before != int(summary.ending_amount):
                raise ValueError(
                    "combat simulation resource summary end does not match event state"
                )
            if calculated_shortfall != int(summary.total_shortfall):
                raise ValueError(
                    "combat simulation resource summary shortfall does not match event evidence"
                )
        health_change_present = any(
            event.event_type == "health_change"
            for event in self.events
        )
        death_present = any(
            event.event_type == "death"
            for event in self.events
        )
        if self.target_state is None:
            if health_change_present:
                raise ValueError(
                    "combat simulation health changes require target state"
                )
            if death_present:
                raise ValueError(
                    "combat simulation death events require target state"
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
            lethal_transition_by_recipient: dict[
                str,
                tuple[float, int, str, str | None, float | None],
            ] = {}
            dead_recipients: set[str] = set()
            for event in self.events:
                if event.event_type not in {"health_change", "death"}:
                    continue
                payload = event.payload_dict()
                recipient = str(payload.get("recipient") or "").strip()
                if not recipient:
                    raise ValueError(
                        f"combat simulation {event.event_type} requires recipient identity"
                    )
                if recipient not in health_by_recipient:
                    raise ValueError(
                        f"combat simulation {event.event_type} recipient is not present in target state"
                    )
                if event.event_type == "death":
                    if recipient in dead_recipients:
                        raise ValueError(
                            "combat simulation death transition cannot be duplicated"
                        )
                    if health_by_recipient[recipient] != 0:
                        raise ValueError(
                            "combat simulation death event requires zero Health state"
                        )
                    expected = lethal_transition_by_recipient.get(recipient)
                    death_overkill = payload.get("overkill")
                    normalized_death_overkill = None
                    if death_overkill is not None:
                        normalized_death_overkill = float(death_overkill)
                        if (
                            not isfinite(normalized_death_overkill)
                            or normalized_death_overkill < 0
                        ):
                            raise ValueError(
                                "combat simulation death overkill must be finite and non-negative"
                            )
                    actual_core = (
                        float(event.time_seconds),
                        int(event.sequence),
                        str(event.source),
                        str(payload.get("origin_event_type") or "").strip() or None,
                    )
                    if expected is None or expected[:4] != actual_core:
                        raise ValueError(
                            "combat simulation death event does not match lethal Health transition"
                        )
                    lethal_overkill = expected[4]
                    if (
                        lethal_overkill is not None
                        and normalized_death_overkill is not None
                        and lethal_overkill != normalized_death_overkill
                    ):
                        raise ValueError(
                            "combat simulation death overkill does not match lethal Health transition"
                        )
                    dead_recipients.add(recipient)
                    continue
                if recipient in dead_recipients:
                    raise ValueError(
                        "combat simulation Health cannot change after death without resurrection semantics"
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
                if maximum is None:
                    raise ValueError(
                        "combat simulation health change requires known maximum Health"
                    )
                if after < 0 or after > int(maximum):
                    raise ValueError(
                        "combat simulation health change after state is outside valid Health bounds"
                    )
                if (
                    "maximum_health" in payload
                    and int(payload["maximum_health"]) != int(maximum)
                ):
                    raise ValueError(
                        "combat simulation health change maximum does not match target state"
                    )
                applied_damage = payload.get("applied_damage")
                applied_heal = payload.get("applied_heal")
                if applied_damage is not None and applied_heal is not None:
                    raise ValueError(
                        "combat simulation health change cannot apply damage and healing together"
                    )
                if applied_damage is not None:
                    applied = float(applied_damage)
                    if not isfinite(applied) or applied < 0:
                        raise ValueError(
                            "combat simulation applied damage must be finite and non-negative"
                        )
                    expected_after = max(0, int(round(float(before) - applied)))
                    if expected_after != after:
                        raise ValueError(
                            "combat simulation damage Health arithmetic is inconsistent"
                        )
                    attempted_damage = payload.get("attempted_damage")
                    overkill = payload.get("overkill")
                    normalized_attempted_damage = None
                    normalized_overkill = None
                    if attempted_damage is not None:
                        normalized_attempted_damage = float(attempted_damage)
                        if (
                            not isfinite(normalized_attempted_damage)
                            or normalized_attempted_damage < 0
                        ):
                            raise ValueError(
                                "combat simulation attempted damage must be finite and non-negative"
                            )
                        if normalized_attempted_damage < applied:
                            raise ValueError(
                                "combat simulation attempted damage cannot be less than applied damage"
                            )
                    if overkill is not None:
                        normalized_overkill = float(overkill)
                        if (
                            not isfinite(normalized_overkill)
                            or normalized_overkill < 0
                        ):
                            raise ValueError(
                                "combat simulation overkill must be finite and non-negative"
                            )
                    if (
                        normalized_attempted_damage is not None
                        and normalized_overkill is not None
                        and normalized_overkill
                        != max(0.0, normalized_attempted_damage - applied)
                    ):
                        raise ValueError(
                            "combat simulation damage overkill arithmetic is inconsistent"
                        )
                if applied_heal is not None:
                    applied = float(applied_heal)
                    if not isfinite(applied) or applied < 0:
                        raise ValueError(
                            "combat simulation applied healing must be finite and non-negative"
                        )
                    expected_after = min(
                        int(maximum),
                        int(round(float(before) + applied)),
                    )
                    if expected_after != after:
                        raise ValueError(
                            "combat simulation healing Health arithmetic is inconsistent"
                        )
                    attempted_heal = payload.get("attempted_heal")
                    overheal = payload.get("overheal")
                    normalized_attempted_heal = None
                    normalized_overheal = None
                    if attempted_heal is not None:
                        normalized_attempted_heal = float(attempted_heal)
                        if (
                            not isfinite(normalized_attempted_heal)
                            or normalized_attempted_heal < 0
                        ):
                            raise ValueError(
                                "combat simulation attempted healing must be finite and non-negative"
                            )
                        if normalized_attempted_heal < applied:
                            raise ValueError(
                                "combat simulation attempted healing cannot be less than applied healing"
                            )
                    if overheal is not None:
                        normalized_overheal = float(overheal)
                        if (
                            not isfinite(normalized_overheal)
                            or normalized_overheal < 0
                        ):
                            raise ValueError(
                                "combat simulation overheal must be finite and non-negative"
                            )
                    if (
                        normalized_attempted_heal is not None
                        and normalized_overheal is not None
                        and normalized_overheal
                        != max(0.0, normalized_attempted_heal - applied)
                    ):
                        raise ValueError(
                            "combat simulation healing overheal arithmetic is inconsistent"
                        )
                health_by_recipient[recipient] = after
                if before > 0 and after == 0:
                    lethal_overkill = payload.get("overkill")
                    normalized_lethal_overkill = None
                    if lethal_overkill is not None:
                        normalized_lethal_overkill = float(lethal_overkill)
                        if (
                            not isfinite(normalized_lethal_overkill)
                            or normalized_lethal_overkill < 0
                        ):
                            raise ValueError(
                                "combat simulation lethal overkill must be finite and non-negative"
                            )
                    lethal_transition_by_recipient[recipient] = (
                        float(event.time_seconds),
                        int(event.sequence),
                        str(event.source),
                        str(payload.get("origin_event_type") or "").strip() or None,
                        normalized_lethal_overkill,
                    )
        window_keys = tuple(
            (
                float(window.start_time_seconds),
                int(window.sequence),
                str(window.effect_name),
                str(window.source),
                str(window.target or ""),
            )
            for window in self.effect_windows
        )
        if window_keys != tuple(sorted(window_keys)):
            raise ValueError(
                "combat simulation effect windows must be in canonical timeline order"
            )
        window_identity_keys = tuple(
            (
                float(window.start_time_seconds),
                float(window.end_time_seconds),
                int(window.sequence),
                str(window.effect_name),
                str(window.source),
                str(window.target or ""),
                window.magnitude,
            )
            for window in self.effect_windows
        )
        if len(set(window_identity_keys)) != len(window_identity_keys):
            raise ValueError(
                "combat simulation effect window identities must be unique"
            )
        if any(
            float(window.start_time_seconds) > duration_seconds
            for window in self.effect_windows
        ):
            raise ValueError(
                "combat simulation effect window cannot start beyond result duration"
            )

        initial_bar = str(self.initial_bar or "").strip().casefold()
        final_bar = str(self.final_bar or "").strip().casefold()
        if initial_bar not in {"front", "back"} or final_bar not in {"front", "back"}:
            raise ValueError(
                "combat simulation result bars must be front or back"
            )
        projected_final_bar = initial_bar
        for event in self.events:
            if event.event_type != "action":
                continue
            payload = event.payload_dict()
            if payload.get("kind") != "bar_swap":
                continue
            destination = str(payload.get("bar") or "").strip().casefold()
            if destination not in {"front", "back"}:
                raise ValueError(
                    "combat simulation bar swap requires front or back destination"
                )
            projected_final_bar = destination
        if projected_final_bar != final_bar:
            raise ValueError(
                "combat simulation final bar does not match event state"
            )
        unresolved = tuple(
            dict.fromkeys(
                str(message).strip()
                for message in self.unresolved
                if str(message).strip()
            )
        )
        damage_unresolved = tuple(
            dict.fromkeys(
                str(message).strip()
                for message in self.damage_unresolved
                if str(message).strip()
            )
        )
        object.__setattr__(self, "duration_seconds", duration_seconds)
        object.__setattr__(self, "initial_bar", initial_bar)
        object.__setattr__(self, "final_bar", final_bar)
        object.__setattr__(self, "unresolved", unresolved)
        object.__setattr__(self, "damage_unresolved", damage_unresolved)

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
