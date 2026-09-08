from __future__ import annotations

from dataclasses import dataclass
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

    def __init__(self, sustain_service: RotationSustainService | None = None) -> None:
        self.sustain_service = sustain_service or RotationSustainService()

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
        initial = self.sustain_service.evaluate(**evaluate_kwargs)
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
                restoration_events=tuple(restoration_events),
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
    ) -> RecoveryPressureResolver:
        """Build generation-ready pressure evidence from the replayed timeline.

        The fallback ``maximum_amount`` preserves compatibility for historical
        timelines. Produced bar-aware timelines carry maximum evidence directly, so
        each pressure decision uses the ceiling active at that exact decision time.
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
            return evaluate_healer_recovery_heavy_pressure(
                timeline=timeline,
                time_seconds=context.time_seconds,
                maximum_amount=active_maximum,
                trigger_fraction=trigger_fraction,
                reserve_assessment=reserve,
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
