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
from services.rotation_healer_canonical_periodic_timing_service import (
    RotationHealerCanonicalPeriodicTimingService,
)
from services.rotation_healer_periodic_runtime_evidence_service import (
    RotationHealerPeriodicRuntimeEvidenceService,
    RotationHealerReviewedRuntimeObservation,
)
from services.rotation_healer_periodic_runtime_service import (
    RotationHealerPeriodicRuntimeService,
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
        canonical_periodic_timing_service: RotationHealerCanonicalPeriodicTimingService | object | None = None,
        periodic_runtime_evidence_service: RotationHealerPeriodicRuntimeEvidenceService | object | None = None,
        periodic_runtime_service: RotationHealerPeriodicRuntimeService | object | None = None,
        reviewed_runtime_observations: tuple[RotationHealerReviewedRuntimeObservation, ...] = (),
    ) -> None:
        self.action_healing_service = (
            action_healing_service
            or RotationHealerActionHealingService(DEFAULT_DATABASE)
        )
        self.static_context_service = (
            static_context_service or RotationStaticBuildContextService()
        )
        self.canonical_periodic_timing_service = (
            canonical_periodic_timing_service
            or RotationHealerCanonicalPeriodicTimingService(DEFAULT_DATABASE)
        )
        self.periodic_runtime_evidence_service = (
            periodic_runtime_evidence_service
            or RotationHealerPeriodicRuntimeEvidenceService()
        )
        self.periodic_runtime_service = (
            periodic_runtime_service or RotationHealerPeriodicRuntimeService()
        )
        self.reviewed_runtime_observations = tuple(reviewed_runtime_observations)

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

        periodic_runtime_events, periodic_unresolved = self._periodic_events(
            projection,
            horizon_seconds=plan.duration_seconds,
        )
        events.extend(periodic_runtime_events)

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
        unresolved.extend(periodic_unresolved)
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

    def _periodic_events(
        self,
        projection: RotationHealerActionHealingProjection,
        *,
        horizon_seconds: float,
    ) -> tuple[tuple[CombatSimulationEvent, ...], tuple[str, ...]]:
        if not projection.periodic_seeds:
            return (), ()

        observations = {
            (item.source_name.casefold(), int(item.coefficient_number)): item
            for item in self.reviewed_runtime_observations
        }
        grouped: dict[tuple[str, int], list[object]] = {}
        for seed in projection.periodic_seeds:
            grouped.setdefault(
                (seed.source_name.casefold(), int(seed.coefficient_number)),
                [],
            ).append(seed)

        evidence = []
        unresolved: list[str] = []
        for key, seeds in grouped.items():
            sample = seeds[0]
            canonical = self.canonical_periodic_timing_service.resolve(
                source_name=sample.source_name,
                coefficient_number=sample.coefficient_number,
            )
            resolution = self.periodic_runtime_evidence_service.resolve(
                canonical=canonical,
                observation=observations.get(key),
                repeated_applications=len(seeds) > 1,
            )
            unresolved.extend(resolution.unresolved)
            if resolution.runtime_evidence is not None:
                evidence.append(resolution.runtime_evidence)

        runtime = self.periodic_runtime_service.project(
            seeds=projection.periodic_seeds,
            evidence=tuple(evidence),
            horizon_seconds=float(horizon_seconds),
        )
        unresolved.extend(runtime.unresolved)

        events = tuple(
            CombatSimulationEvent(
                time_seconds=float(item.time_seconds),
                priority=int(SimulationEventPriority.PERIODIC),
                sequence=int(item.sequence),
                event_type="periodic_heal",
                source=item.source_name,
                payload=(
                    ("coefficient_number", int(item.coefficient_number)),
                    ("modeled_heal", float(item.modeled_heal)),
                ),
            )
            for item in runtime.events
        )
        return events, tuple(
            dict.fromkeys(
                str(message).strip()
                for message in unresolved
                if str(message).strip()
            )
        )


__all__ = [
    "CombatSimulationHealingProjection",
    "CombatSimulationHealingService",
]
