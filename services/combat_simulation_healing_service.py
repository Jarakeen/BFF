from __future__ import annotations

"""Bridge canonical healer output into Phase 14 simulation events."""

from dataclasses import dataclass

from engine.config import DEFAULT_DATABASE
from models.build_model import PlayerBuild
from models.combat_simulation import CombatSimulationEvent, SimulationEventPriority
from minmax.rotation_plan import RotationPlan
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingProjection,
    RotationHealerActionHealingService,
)
from services.rotation_static_build_context_service import RotationStaticBuildContextService


@dataclass(frozen=True)
class CombatSimulationHealingProjection:
    events: tuple[CombatSimulationEvent, ...]
    unresolved: tuple[str, ...] = ()


class CombatSimulationHealingService:
    """Project healer actions through the existing canonical healer engines.

    Direct heals become concrete simulation results. Periodic/delayed/channel
    components remain explicit seeds until their canonical runtime timing layer
    supplies event placement. This service never fabricates tick cadence.
    """

    def __init__(
        self,
        *,
        action_healing_service: RotationHealerActionHealingService | object | None = None,
        static_context_service: RotationStaticBuildContextService | object | None = None,
    ) -> None:
        self.action_healing_service = (
            action_healing_service
            or RotationHealerActionHealingService(DEFAULT_DATABASE)
        )
        self.static_context_service = (
            static_context_service or RotationStaticBuildContextService()
        )

    def project(
        self,
        *,
        build: PlayerBuild,
        plan: RotationPlan,
    ) -> CombatSimulationHealingProjection:
        contexts = self.static_context_service.resolve(build)
        if not contexts.resolved:
            unresolved = tuple(
                dict.fromkeys(
                    str(message).strip()
                    for message in contexts.unresolved
                    if str(message).strip()
                )
            )
            if not unresolved:
                unresolved = ("canonical healer build context is unresolved",)
            return CombatSimulationHealingProjection(events=(), unresolved=unresolved)

        front = contexts.context_for("front")
        if front is None:
            return CombatSimulationHealingProjection(
                events=(),
                unresolved=("canonical healer front-bar context is unavailable",),
            )

        projection: RotationHealerActionHealingProjection = (
            self.action_healing_service.project(
                plan=plan,
                build=build,
                context=front,
                contexts_by_bar={
                    context.active_bar: context for context in contexts.contexts
                },
            )
        )

        events: list[CombatSimulationEvent] = []
        for item in projection.direct_events:
            events.append(
                CombatSimulationEvent(
                    time_seconds=float(item.time_seconds),
                    priority=int(SimulationEventPriority.DIRECT_RESULT),
                    sequence=int(item.sequence),
                    event_type="direct_heal",
                    source=item.source_name,
                    payload=(
                        ("coefficient_number", int(item.coefficient_number)),
                        ("modeled_heal", float(item.modeled_heal)),
                    ),
                )
            )

        for item in projection.periodic_seeds:
            events.append(
                CombatSimulationEvent(
                    time_seconds=float(item.time_seconds),
                    priority=int(SimulationEventPriority.TRIGGER),
                    sequence=int(item.sequence),
                    event_type="periodic_heal_seed",
                    source=item.source_name,
                    payload=(
                        ("coefficient_number", int(item.coefficient_number)),
                        ("modeled_heal", float(item.modeled_heal)),
                    ),
                )
            )

        for item in projection.delayed_seeds:
            events.append(
                CombatSimulationEvent(
                    time_seconds=float(item.time_seconds),
                    priority=int(SimulationEventPriority.TRIGGER),
                    sequence=int(item.sequence),
                    event_type="delayed_heal_seed",
                    source=item.source_name,
                    payload=(
                        ("coefficient_number", int(item.coefficient_number)),
                        ("modeled_heal", float(item.modeled_heal)),
                    ),
                )
            )

        for item in projection.channel_seeds:
            events.append(
                CombatSimulationEvent(
                    time_seconds=float(item.time_seconds),
                    priority=int(SimulationEventPriority.TRIGGER),
                    sequence=int(item.sequence),
                    event_type="channel_heal_seed",
                    source=item.source_name,
                    payload=(
                        ("coefficient_number", int(item.coefficient_number)),
                        ("modeled_heal", float(item.modeled_heal)),
                    ),
                )
            )

        unresolved = list(projection.unresolved)
        for item in projection.periodic_seeds:
            unresolved.append(
                f"{item.source_name} coefficient {item.coefficient_number}: "
                "periodic healing magnitude is resolved but exact tick events require "
                "reviewed runtime timing evidence"
            )
        for item in projection.delayed_seeds:
            unresolved.append(
                f"{item.source_name} coefficient {item.coefficient_number}: "
                "delayed healing magnitude is resolved but exact event timing is unresolved"
            )
        for item in projection.channel_seeds:
            unresolved.append(
                f"{item.source_name} coefficient {item.coefficient_number}: "
                "channel healing magnitude is resolved but exact tick timing is unresolved"
            )

        return CombatSimulationHealingProjection(
            events=tuple(
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
            ),
            unresolved=tuple(
                dict.fromkeys(
                    str(message).strip()
                    for message in unresolved
                    if str(message).strip()
                )
            ),
        )


__all__ = [
    "CombatSimulationHealingProjection",
    "CombatSimulationHealingService",
]
