from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from models.build_model import PlayerBuild

from .build_action_cost_modifiers import BuildActionCostModifierResolver
from .build_calculation_context import BuildCalculationContext
from .conditional_recovery import TimedRecoveryModifier
from .final_action_cost import calculate_final_action_cost
from .recovery_timing import (
    RecoveryActivityResolver,
    ScheduledRecoveryTick,
    schedule_in_combat_recovery_ticks,
)
from .resource_costs import BaseActionCost, ResourceType
from .resource_state import StaticResourceState
from .resource_timeline import (
    ResourceCostEvent,
    ResourceTimelineResult,
    create_action_cost_events,
    run_resource_timeline,
)
from .restoration_events import ResourceRestorationEvent
from .sustain_result import SustainResult, summarize_sustain


@dataclass(frozen=True)
class PlannedBuildAction:
    """One verified resolved action placed on a saved-build sustain plan."""

    time_seconds: float
    source: str
    base_cost: BaseActionCost
    skill_line: str | None = None

    def __post_init__(self) -> None:
        if self.time_seconds < 0:
            raise ValueError(f"Planned action time cannot be negative: {self.time_seconds}")
        if not str(self.source or "").strip():
            raise ValueError("Planned action requires a source")


@dataclass(frozen=True)
class BuildSustainRun:
    """Auditable Phase 4 sustain evaluation for one saved build/resource."""

    resource: ResourceType
    action_cost_events: tuple[ResourceCostEvent, ...]
    recovery_ticks: tuple[ScheduledRecoveryTick, ...]
    restoration_events: tuple[ResourceRestorationEvent, ...]
    timeline: ResourceTimelineResult
    sustain: SustainResult
    unresolved: tuple[str, ...]


def evaluate_build_sustain(
    *,
    build: PlayerBuild,
    context: BuildCalculationContext,
    resource: ResourceType,
    duration_seconds: float,
    actions: tuple[PlannedBuildAction, ...],
    cost_modifier_resolver: BuildActionCostModifierResolver,
    restoration_events: tuple[ResourceRestorationEvent, ...] = (),
    recovery_modifiers: tuple[TimedRecoveryModifier, ...] = (),
    activity_at: RecoveryActivityResolver | None = None,
    starting_amount: int | None = None,
    first_recovery_tick_seconds: float = 2.0,
) -> BuildSustainRun:
    """Run a saved build through the verified Phase 4 sustain pipeline.

    The saved build supplies build-specific cost modifiers while the immutable
    calculation context supplies the already-audited character sheet state and
    progression. Actions must already have canonical ``BaseActionCost`` values;
    name-to-ability lookup remains a separate repository concern.

    Only events for the requested resource enter the single-resource timeline.
    Unsupported build cost modifiers remain explicit in ``unresolved``.
    """

    duration = float(duration_seconds)
    if duration < 0:
        raise ValueError(f"Sustain duration cannot be negative: {duration_seconds}")
    if resource is ResourceType.ULTIMATE:
        raise ValueError("Saved-build sustain runner currently models primary resource pools only")

    static_state = StaticResourceState.from_base_character_state(context.character_state)
    pool = static_state.pool(resource)
    initial = pool.maximum if starting_amount is None else int(starting_amount)

    resolved_modifiers = cost_modifier_resolver.resolve(
        build,
        progression=context.progression,
    )

    cost_events: list[ResourceCostEvent] = []
    for action in actions:
        if action.time_seconds > duration:
            continue
        final_cost = calculate_final_action_cost(
            action.base_cost,
            resolved_modifiers.modifiers,
            skill_line=action.skill_line,
        )
        cost_events.extend(
            event
            for event in create_action_cost_events(
                time_seconds=action.time_seconds,
                final_cost=final_cost,
                source=action.source,
            )
            if event.resource is resource
        )

    recovery_ticks = schedule_in_combat_recovery_ticks(
        pool,
        duration_seconds=duration,
        first_tick_seconds=first_recovery_tick_seconds,
        activity_at=activity_at,
        recovery_modifiers=recovery_modifiers,
    )

    resource_restores = tuple(
        event
        for event in restoration_events
        if event.resource is resource and event.time_seconds <= duration
    )

    timeline = run_resource_timeline(
        pool,
        starting_amount=initial,
        cost_events=tuple(cost_events),
        recovery_ticks=recovery_ticks,
        restoration_events=resource_restores,
    )

    return BuildSustainRun(
        resource=resource,
        action_cost_events=tuple(cost_events),
        recovery_ticks=recovery_ticks,
        restoration_events=resource_restores,
        timeline=timeline,
        sustain=summarize_sustain(timeline),
        unresolved=resolved_modifiers.unresolved,
    )
