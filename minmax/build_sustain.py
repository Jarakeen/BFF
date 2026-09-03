from __future__ import annotations

from dataclasses import dataclass
from weakref import WeakKeyDictionary

from models.build_model import PlayerBuild

from .ability_cost_repository import AbilityCostRepository
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
class NamedBuildAction:
    """One saved skill name placed at an explicit time on a sustain plan."""

    time_seconds: float
    skill_name: str

    def __post_init__(self) -> None:
        if self.time_seconds < 0:
            raise ValueError(f"Named action time cannot be negative: {self.time_seconds}")
        if not str(self.skill_name or "").strip():
            raise ValueError("Named action requires a skill name")


@dataclass(frozen=True)
class NamedBuildActionResolution:
    """Immutable named-action plan resolved once against canonical ability costs."""

    actions: tuple[PlannedBuildAction, ...]
    unresolved: tuple[str, ...] = ()


_NAMED_ACTION_PLAN_CACHE: WeakKeyDictionary[
    AbilityCostRepository,
    dict[tuple[NamedBuildAction, ...], NamedBuildActionResolution],
] = WeakKeyDictionary()


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


def resolve_named_build_actions(
    actions: tuple[NamedBuildAction, ...],
    *,
    ability_cost_repository: AbilityCostRepository,
) -> NamedBuildActionResolution:
    """Resolve a stable saved-bar action plan once for repeated sustain runs.

    Resolution is cached for the lifetime of the supplied ability-cost repository.
    That gives repeated candidate evaluations one immutable action plan while a
    fresh repository still observes later canonical database changes.
    """

    action_key = tuple(actions)
    repository_cache = _NAMED_ACTION_PLAN_CACHE.setdefault(ability_cost_repository, {})
    cached = repository_cache.get(action_key)
    if cached is not None:
        return cached

    resolved_actions: list[PlannedBuildAction] = []
    unresolved: list[str] = []

    for action in action_key:
        resolution = ability_cost_repository.resolve_name(action.skill_name)
        if resolution.base_cost is None:
            if resolution.unresolved:
                unresolved.extend(
                    f"{action.skill_name}: {message}" for message in resolution.unresolved
                )
            else:
                unresolved.append(f"{action.skill_name}: action cost could not be resolved")
            continue

        # Coefficient absence is relevant to damage/healing evaluation but not
        # to resource cost. Keep only cost-resolution failures here rather than
        # turning a valid resource action into a false sustain warning.
        cost_unresolved = tuple(
            message
            for message in resolution.unresolved
            if not message.startswith("No coefficient rows found")
        )
        unresolved.extend(f"{action.skill_name}: {message}" for message in cost_unresolved)
        resolved_actions.append(
            PlannedBuildAction(
                time_seconds=action.time_seconds,
                source=resolution.name or action.skill_name,
                base_cost=resolution.base_cost,
                skill_line=resolution.skill_line,
            )
        )

    result = NamedBuildActionResolution(
        actions=tuple(resolved_actions),
        unresolved=tuple(unresolved),
    )
    repository_cache[action_key] = result
    return result


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
    additional_unresolved: tuple[str, ...] = (),
) -> BuildSustainRun:
    """Run a saved build through the verified Phase 4 sustain pipeline.

    The saved build supplies build-specific cost modifiers while the immutable
    calculation context supplies the already-audited character sheet state and
    progression. This lower-level entry point accepts already-canonical
    ``BaseActionCost`` actions; ``evaluate_named_build_sustain`` owns the
    name-to-ability lookup bridge.

    Only events for the requested resource enter the single-resource timeline.
    Unsupported cost or action resolution remains explicit in ``unresolved``.
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
        unresolved=resolved_modifiers.unresolved + tuple(additional_unresolved),
    )


def evaluate_named_build_sustain(
    *,
    build: PlayerBuild,
    context: BuildCalculationContext,
    resource: ResourceType,
    duration_seconds: float,
    actions: tuple[NamedBuildAction, ...],
    ability_cost_repository: AbilityCostRepository,
    cost_modifier_resolver: BuildActionCostModifierResolver,
    restoration_events: tuple[ResourceRestorationEvent, ...] = (),
    recovery_modifiers: tuple[TimedRecoveryModifier, ...] = (),
    activity_at: RecoveryActivityResolver | None = None,
    starting_amount: int | None = None,
    first_recovery_tick_seconds: float = 2.0,
) -> BuildSustainRun:
    """Resolve named saved skills and run them through the Phase 4 pipeline."""

    resolution = resolve_named_build_actions(
        actions,
        ability_cost_repository=ability_cost_repository,
    )
    return evaluate_build_sustain(
        build=build,
        context=context,
        resource=resource,
        duration_seconds=duration_seconds,
        actions=resolution.actions,
        cost_modifier_resolver=cost_modifier_resolver,
        restoration_events=restoration_events,
        recovery_modifiers=recovery_modifiers,
        activity_at=activity_at,
        starting_amount=starting_amount,
        first_recovery_tick_seconds=first_recovery_tick_seconds,
        additional_unresolved=resolution.unresolved,
    )
