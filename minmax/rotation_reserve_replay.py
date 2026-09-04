from __future__ import annotations

from dataclasses import dataclass

from .recovery_timing import ScheduledRecoveryTick
from .resource_state import StaticResourcePool
from .resource_timeline import ResourceCostEvent, ResourceTimelineResult, run_resource_timeline
from .restoration_events import ResourceRestorationEvent
from .rotation_reserve_priority import (
    ReserveProtectionPriority,
    RotationReserveProtectionPlan,
    plan_rotation_reserve_protection,
)
from .rotation_reserve_protection import (
    DiscretionaryRotationSpend,
    RotationReserveProtectionAnalysis,
)
from .rotation_resource_reserve import (
    RotationResourceReserveAssessment,
    assess_rotation_resource_reserve,
)


@dataclass(frozen=True)
class ResourceTimelineReplayInputs:
    """Raw verified inputs needed to replay one resource timeline exactly."""

    pool: StaticResourcePool
    starting_amount: int
    cost_events: tuple[ResourceCostEvent, ...]
    recovery_ticks: tuple[ScheduledRecoveryTick, ...] = ()
    restoration_events: tuple[ResourceRestorationEvent, ...] = ()


@dataclass(frozen=True)
class ExactReserveProtectionPlan:
    """Reserve-protection result proven by exact timeline replay.

    The embedded generic protection plan keeps the existing adjustment contract,
    but its selected prefix and projected entry amount come from replay rather
    than arithmetic cost recovery.
    """

    protection_plan: RotationReserveProtectionPlan
    replayed_timeline: ResourceTimelineResult
    replayed_assessment: RotationResourceReserveAssessment


def replay_resource_timeline_with_withheld_spends(
    *,
    inputs: ResourceTimelineReplayInputs,
    withheld_spends: tuple[DiscretionaryRotationSpend, ...],
) -> ResourceTimelineResult:
    """Replay the canonical resource simulator after removing exact action costs.

    Each withheld declaration must match exactly one raw cost event. Recovery and
    restoration events are left untouched, allowing the existing simulator to
    recalculate cap waste and downstream state changes correctly.
    """

    seen: set[tuple[float, str]] = set()
    remove_ids: set[int] = set()

    for withheld in withheld_spends:
        key = (float(withheld.time_seconds), withheld.source)
        if key in seen:
            raise ValueError(
                f"duplicate replay withholding declaration: {withheld.source} at {withheld.time_seconds:g}s"
            )
        seen.add(key)

        matches = tuple(
            event
            for event in inputs.cost_events
            if event.time_seconds == withheld.time_seconds and event.source == withheld.source
        )
        if not matches:
            raise ValueError(
                "replay withholding does not match an action cost: "
                f"{withheld.source} at {withheld.time_seconds:g}s"
            )
        if len(matches) > 1:
            raise ValueError(
                "replay withholding is ambiguous on the resource timeline: "
                f"{withheld.source} at {withheld.time_seconds:g}s"
            )
        remove_ids.add(id(matches[0]))

    return run_resource_timeline(
        inputs.pool,
        starting_amount=inputs.starting_amount,
        cost_events=tuple(event for event in inputs.cost_events if id(event) not in remove_ids),
        recovery_ticks=inputs.recovery_ticks,
        restoration_events=inputs.restoration_events,
    )


def plan_exact_rotation_reserve_protection(
    *,
    analysis: RotationReserveProtectionAnalysis,
    priorities: tuple[ReserveProtectionPriority, ...],
    replay_inputs: ResourceTimelineReplayInputs,
) -> ExactReserveProtectionPlan:
    """Select the smallest policy prefix that actually repairs reserve on replay.

    Existing priority validation/ranking is reused, but its arithmetic selection
    is ignored. Each policy prefix is replayed through ``run_resource_timeline``;
    selection stops only when the replayed entry reserve satisfies the original
    demand requirement. If all candidates are insufficient, all are selected and
    the remaining shortfall stays explicit.
    """

    ranked_template = plan_rotation_reserve_protection(
        analysis=analysis,
        priorities=priorities,
    )

    ranked = ranked_template.ranked_candidates
    selected = []
    replayed = replay_resource_timeline_with_withheld_spends(
        inputs=replay_inputs,
        withheld_spends=(),
    )
    assessment = assess_rotation_resource_reserve(
        timeline=replayed,
        demand=analysis.demand,
        requirement=analysis.reserve_assessment.requirement,
    )

    expected_baseline = analysis.reserve_assessment.available_before_start
    if assessment.available_before_start != expected_baseline:
        raise ValueError(
            "reserve replay inputs do not reproduce analyzed demand-entry resource: "
            f"{assessment.available_before_start} != {expected_baseline}"
        )

    if not assessment.satisfied:
        for item in ranked:
            selected.append(item)
            replayed = replay_resource_timeline_with_withheld_spends(
                inputs=replay_inputs,
                withheld_spends=tuple(
                    DiscretionaryRotationSpend(
                        time_seconds=selected_item.candidate.time_seconds,
                        source=selected_item.candidate.source,
                    )
                    for selected_item in selected
                ),
            )
            assessment = assess_rotation_resource_reserve(
                timeline=replayed,
                demand=analysis.demand,
                requirement=analysis.reserve_assessment.requirement,
            )
            if assessment.satisfied:
                break

    exact_plan = RotationReserveProtectionPlan(
        analysis=analysis,
        ranked_candidates=ranked,
        selected_to_withhold=tuple(selected),
        projected_available_after_selected=assessment.available_before_start,
    )

    return ExactReserveProtectionPlan(
        protection_plan=exact_plan,
        replayed_timeline=replayed,
        replayed_assessment=assessment,
    )
