from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from minmax.build_calculation_context import BuildCalculationContext
from minmax.healer_recovery_heavy_pressure import (
    HealerRecoveryHeavyPressure,
    evaluate_healer_recovery_heavy_pressure,
)
from minmax.recovery_timing import DisplayedRecoveryResolver
from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceMaximumEvent
from minmax.restoration_events import ResourceRestorationEvent
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_resource_reserve import RotationResourceReserveAssessment
from minmax.rotation_wait_decision import PrematureRecastDecisionContext
from models.build_model import PlayerBuild
from services.rotation_sustain_service import RotationSustainProjection, RotationSustainService
from services.rotation_plan_potion_combat_state_service import RotationPlanPotionCombatStateService


VerifiedRecoveryHeavyRestorationResolver = Callable[
    [RotationAction],
    ResourceRestorationEvent | None,
]
RecoveryReserveAssessmentResolver = Callable[
    [PrematureRecastDecisionContext],
    RotationResourceReserveAssessment | None,
]
RecoveryPressureResolver = Callable[
    [PrematureRecastDecisionContext],
    HealerRecoveryHeavyPressure | None,
]


@dataclass(frozen=True)
class RotationRecoveryHeavyReplayStep:
    """One scheduled recovery heavy applied to a freshly replayed sustain timeline."""

    heavy_action: RotationAction
    restoration_event: ResourceRestorationEvent
    projection: RotationSustainProjection


@dataclass(frozen=True)
class RotationRecoveryHeavyReplay:
    """Iterative sustain replay after caller-verified heavy-attack restores."""

    initial_projection: RotationSustainProjection
    final_projection: RotationSustainProjection
    restoration_events: tuple[ResourceRestorationEvent, ...]
    steps: tuple[RotationRecoveryHeavyReplayStep, ...]


class RotationRecoveryHeavyReplayService:
    """Replay sustain after each scheduled heavy with verified restoration evidence.

    This service deliberately does not infer restore amounts, resource ceilings, or
    displayed recovery values. The rotation scheduler owns placement, callers own
    verified restoration/ceiling/recovery evidence, and the Phase 4 timeline owns
    ordering, capping, clipping, waste, and shortfall.
    """

    def __init__(
        self,
        sustain_service: RotationSustainService | None = None,
        *,
        potion_runtime_service: RotationPlanPotionCombatStateService | None = None,
    ) -> None:
        self.sustain_service = sustain_service or RotationSustainService()
        self.potion_runtime_service = potion_runtime_service or RotationPlanPotionCombatStateService()

    def replay(
        self,
        *,
        build: PlayerBuild,
        plan: RotationPlan,
        resource: ResourceType,
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver,
        maximum_events: tuple[ResourceMaximumEvent, ...] = (),
        calculation_context: BuildCalculationContext | None = None,
        displayed_recovery_at: DisplayedRecoveryResolver | None = None,
    ) -> RotationRecoveryHeavyReplay:
        evaluate_kwargs = dict(
            build=build,
            plan=plan,
            resource=resource,
            maximum_events=tuple(maximum_events),
            calculation_context=calculation_context,
            displayed_recovery_at=displayed_recovery_at,
        )
        potion_restoration = self.potion_runtime_service.resolve_restoration_events(
            build,
            plan=plan,
        )
        potion_restoration_events = tuple(potion_restoration.events)
        potion_unresolved = tuple(potion_restoration.unresolved)
        initial = self.sustain_service.evaluate(
            **evaluate_kwargs,
            restoration_events=potion_restoration_events,
        )
        if potion_unresolved:
            initial = replace(
                initial,
                unresolved=tuple(
                    dict.fromkeys((*tuple(initial.unresolved), *potion_unresolved))
                ),
            )
        current = initial
        restoration_events: list[ResourceRestorationEvent] = []
        steps: list[RotationRecoveryHeavyReplayStep] = []

        heavies = sorted(
            (
                action
                for action in plan.actions
                if action.kind is RotationActionKind.HEAVY_ATTACK
            ),
            key=lambda action: (action.time_seconds, action.sequence),
        )

        for heavy in heavies:
            event = restoration_resolver(heavy)
            if event is None:
                continue
            self._validate_event(
                event=event,
                heavy=heavy,
                plan=plan,
                resource=resource,
            )
            restoration_events.append(event)
            current = self.sustain_service.evaluate(
                **evaluate_kwargs,
                restoration_events=potion_restoration_events + tuple(restoration_events),
            )
            if potion_unresolved:
                current = replace(
                    current,
                    unresolved=tuple(
                        dict.fromkeys((*tuple(current.unresolved), *potion_unresolved))
                    ),
                )
            steps.append(
                RotationRecoveryHeavyReplayStep(
                    heavy_action=heavy,
                    restoration_event=event,
                    projection=current,
                )
            )

        return RotationRecoveryHeavyReplay(
            initial_projection=initial,
            final_projection=current,
            restoration_events=tuple(restoration_events),
            steps=tuple(steps),
        )

    @staticmethod
    def pressure_resolver(
        *,
        replay: RotationRecoveryHeavyReplay,
        maximum_amount: int,
        trigger_fraction: float,
        reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None,
        anticipate_future_shortfall: bool = False,
    ) -> RecoveryPressureResolver:
        """Build generation-ready pressure evidence from the replayed timeline.

        The fallback ``maximum_amount`` preserves compatibility for historical
        timelines. Produced bar-aware timelines carry maximum evidence directly, so
        each pressure decision uses the ceiling active at that exact decision time.

        When ``anticipate_future_shortfall`` is enabled, a legal recovery-heavy
        decision point may be recommended before the ordinary low-resource threshold
        is crossed when the already-replayed plan proves that a resource shortfall
        occurs later in the same horizon. This lets a "prefer safe windows" policy
        recover while a channel window still exists instead of waiting until the bar
        is already empty and the last safe window has passed.
        """

        timeline = replay.final_projection.run.timeline

        def resolve(
            context: PrematureRecastDecisionContext,
        ) -> HealerRecoveryHeavyPressure:
            reserve = (
                reserve_assessment_resolver(context)
                if reserve_assessment_resolver is not None
                else None
            )
            active_maximum = timeline.maximum_at(
                context.time_seconds,
                fallback=int(maximum_amount),
            )
            pressure = evaluate_healer_recovery_heavy_pressure(
                timeline=timeline,
                time_seconds=context.time_seconds,
                maximum_amount=active_maximum,
                trigger_fraction=trigger_fraction,
                reserve_assessment=reserve,
            )
            if pressure.recommended or not anticipate_future_shortfall:
                return pressure

            future_shortfall = sum(
                int(event.shortfall)
                for event in timeline.events
                if float(event.time_seconds) > float(context.time_seconds)
            )
            if future_shortfall <= 0:
                return pressure

            return replace(
                pressure,
                reserve_shortfall=future_shortfall,
                recommended=True,
                reason=(
                    f"the current {timeline.resource.value} pool is above the "
                    f"{float(trigger_fraction):.1%} recovery trigger, but the replayed "
                    f"rotation proves a later shortfall of {future_shortfall}; recover "
                    "during this earlier legal window"
                ),
            )

        return resolve

    @staticmethod
    def _validate_event(
        *,
        event: ResourceRestorationEvent,
        heavy: RotationAction,
        plan: RotationPlan,
        resource: ResourceType,
    ) -> None:
        if event.resource is not resource:
            raise ValueError(
                "recovery-heavy restoration resource does not match replay resource: "
                f"{event.resource.value} != {resource.value}"
            )
        if event.time_seconds < heavy.time_seconds:
            raise ValueError(
                "recovery-heavy restoration cannot occur before the scheduled heavy starts"
            )
        if event.time_seconds > plan.duration_seconds:
            raise ValueError(
                "recovery-heavy restoration cannot occur after the rotation plan horizon"
            )
