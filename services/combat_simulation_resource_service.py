from __future__ import annotations

"""Phase 14 adapter from canonical Rotation sustain into simulation events."""

from dataclasses import dataclass

from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceTimelineEventKind
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from models.combat_simulation import (
    CombatSimulationEvent,
    CombatSimulationResourceResult,
    SimulationEventPriority,
)
from services.rotation_sustain_service import RotationSustainService


@dataclass(frozen=True)
class CombatSimulationResourceProjection:
    result: CombatSimulationResourceResult
    events: tuple[CombatSimulationEvent, ...]
    unresolved: tuple[str, ...] = ()


class CombatSimulationResourceService:
    """Project one resource through the existing Phase 4/13 sustain authority."""

    def __init__(
        self,
        *,
        sustain_service: RotationSustainService | None = None,
    ) -> None:
        self.sustain_service = sustain_service or RotationSustainService()

    def project(
        self,
        *,
        build: PlayerBuild,
        plan: RotationPlan,
        resource: ResourceType,
    ) -> CombatSimulationResourceProjection:
        projection = self.sustain_service.evaluate(
            build=build,
            plan=plan,
            resource=resource,
        )
        timeline = projection.run.timeline
        if timeline.resource is not resource:
            raise ValueError(
                "resource timeline identity does not match requested simulation resource"
            )

        events: list[CombatSimulationEvent] = []
        sequence = 0
        prior_order_key: tuple[float, int] | None = None
        prior_after = int(timeline.starting_amount)
        for item in timeline.events:
            if item.kind is ResourceTimelineEventKind.ACTION_COST:
                priority = SimulationEventPriority.RESOURCE_COST
            elif item.kind in {
                ResourceTimelineEventKind.RECOVERY_TICK,
                ResourceTimelineEventKind.RESTORATION,
            }:
                priority = SimulationEventPriority.RESOURCE_RESTORE
            elif item.kind is ResourceTimelineEventKind.RESOURCE_MAXIMUM:
                priority = SimulationEventPriority.RESOURCE_MAXIMUM
            else:
                priority = SimulationEventPriority.SNAPSHOT

            order_key = (float(item.time_seconds), int(priority))
            if prior_order_key is not None and order_key < prior_order_key:
                raise ValueError(
                    "resource timeline events are not in canonical simulation order"
                )
            prior_order_key = order_key
            before = int(item.before)
            applied_change = int(item.applied_change)
            after = int(item.after)
            if before != prior_after:
                raise ValueError(
                    "resource timeline before/after chain is inconsistent"
                )
            if before + applied_change != after:
                raise ValueError(
                    "resource timeline event arithmetic is inconsistent"
                )
            attempted_change = int(item.attempted_change)
            shortfall = int(item.shortfall)
            wasted_restore = int(item.wasted_restore)
            if shortfall < 0 or wasted_restore < 0:
                raise ValueError(
                    "resource timeline shortfall and wasted restore cannot be negative"
                )
            if item.kind is ResourceTimelineEventKind.ACTION_COST:
                if attempted_change > 0 or applied_change > 0:
                    raise ValueError(
                        "resource action cost changes must be non-positive"
                    )
                if wasted_restore != 0:
                    raise ValueError(
                        "resource action cost cannot record wasted restore"
                    )
                if shortfall != abs(attempted_change) - abs(applied_change):
                    raise ValueError(
                        "resource action cost shortfall arithmetic is inconsistent"
                    )
            elif item.kind in {
                ResourceTimelineEventKind.RECOVERY_TICK,
                ResourceTimelineEventKind.RESTORATION,
            }:
                if attempted_change < 0 or applied_change < 0:
                    raise ValueError(
                        "resource restore changes must be non-negative"
                    )
                if shortfall != 0:
                    raise ValueError(
                        "resource restore cannot record action-cost shortfall"
                    )
                if wasted_restore != attempted_change - applied_change:
                    raise ValueError(
                        "resource wasted restore arithmetic is inconsistent"
                    )
            elif item.kind is ResourceTimelineEventKind.RESOURCE_MAXIMUM:
                if attempted_change != 0 or shortfall != 0 or wasted_restore != 0:
                    raise ValueError(
                        "resource maximum change carries invalid resource delta evidence"
                    )
            prior_after = after

            events.append(
                CombatSimulationEvent(
                    time_seconds=float(item.time_seconds),
                    priority=int(priority),
                    sequence=sequence,
                    event_type=item.kind.value,
                    source=str(item.source),
                    payload=(
                        ("resource", resource.value),
                        ("before", before),
                        ("attempted_change", attempted_change),
                        ("applied_change", applied_change),
                        ("after", after),
                        ("shortfall", shortfall),
                        ("wasted_restore", wasted_restore),
                    ),
                )
            )
            sequence += 1

        if prior_after != int(timeline.ending_amount):
            raise ValueError(
                "resource timeline ending amount does not match final event state"
            )

        return CombatSimulationResourceProjection(
            result=CombatSimulationResourceResult(
                resource=resource.value,
                starting_amount=int(timeline.starting_amount),
                ending_amount=int(timeline.ending_amount),
                total_shortfall=int(timeline.total_shortfall),
            ),
            events=tuple(events),
            unresolved=tuple(projection.unresolved),
        )


__all__ = [
    "CombatSimulationResourceProjection",
    "CombatSimulationResourceService",
]
