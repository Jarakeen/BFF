from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from minmax.build_calculation_context import BuildCalculationContext
from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceMaximumEvent
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.runtime_healer_wait_decision_provider import RecoveryHeavyPressureResolver
from models.build_model import PlayerBuild
from services.rotation_recovery_heavy_replay_service import (
    RecoveryReserveAssessmentResolver,
    RotationRecoveryHeavyReplay,
    RotationRecoveryHeavyReplayService,
    VerifiedRecoveryHeavyRestorationResolver,
)


RecoveryAwareRotationGenerator = Callable[
    [RecoveryHeavyPressureResolver | None],
    RotationPlan,
]
RecoveryHardObligationStateResolver = Callable[
    [RotationPlan, RotationRecoveryHeavyReplay],
    tuple[str, ...],
]
RecoveryMaximumEventResolver = Callable[
    [RotationPlan, ResourceType],
    tuple[ResourceMaximumEvent, ...],
]
RecoveryDisplayedRecoveryResolverFactory = Callable[
    [RotationPlan, ResourceType],
    Callable[[float], int],
]
RecoveryRestorationResolverFactory = Callable[
    [RotationPlan],
    VerifiedRecoveryHeavyRestorationResolver,
]


@dataclass(frozen=True)
class RotationRecoveryHeavyStabilizationIteration:
    """One generate -> replay step in recovery-heavy schedule stabilization."""

    iteration: int
    plan: RotationPlan
    replay: RotationRecoveryHeavyReplay
    heavy_signature: tuple[tuple[float, int, str | None, str | None], ...]
    plan_signature: tuple[object, ...]
    minimum_resource: int
    total_shortfall: int
    hard_obligation_state: tuple[str, ...]

    @property
    def tracked_hard_obligations_satisfied(self) -> bool:
        return self.total_shortfall == 0 and not self.hard_obligation_state


@dataclass(frozen=True)
class RotationRecoveryHeavyStabilizationResult:
    """Bounded fixed-point result for recovery-heavy rotation generation."""

    plan: RotationPlan
    replay: RotationRecoveryHeavyReplay
    iterations: tuple[RotationRecoveryHeavyStabilizationIteration, ...]
    converged: bool
    termination_reason: str

    @property
    def tracked_hard_obligations_satisfied(self) -> bool:
        if not self.iterations:
            return False
        return self.iterations[-1].tracked_hard_obligations_satisfied


class RotationRecoveryHeavyStabilizationService:
    """Regenerate recovery-heavy rotations until complete schedule state stabilizes.

    Each iteration generates a plan from the latest pressure resolver, derives any
    caller-verified bar-sensitive resource-ceiling events and displayed recovery for
    that *actual* plan, then replays sustain with the canonical static calculation
    context. The next pressure resolver therefore observes the same bar-aware
    resource history that produced the candidate's hard-obligation state.

    A legacy/static restoration resolver may still be supplied directly. Canonical
    callers whose restoration evidence depends on the regenerated plan may instead
    supply ``restoration_resolver_factory``; it is invoked once for each generated
    plan before that plan is replayed. Supplying both paths is rejected so restore
    evidence can never be silently double-sourced.
    """

    def __init__(
        self,
        replay_service: RotationRecoveryHeavyReplayService | None = None,
    ) -> None:
        self.replay_service = replay_service or RotationRecoveryHeavyReplayService()

    def stabilize(
        self,
        *,
        build: PlayerBuild,
        generate: RecoveryAwareRotationGenerator,
        resource: ResourceType,
        maximum_amount: int,
        trigger_fraction: float,
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver | None = None,
        restoration_resolver_factory: RecoveryRestorationResolverFactory | None = None,
        reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None,
        hard_obligation_state_resolver: RecoveryHardObligationStateResolver | None = None,
        max_iterations: int = 6,
        calculation_context: BuildCalculationContext | None = None,
        maximum_event_resolver: RecoveryMaximumEventResolver | None = None,
        displayed_recovery_resolver_factory: RecoveryDisplayedRecoveryResolverFactory | None = None,
    ) -> RotationRecoveryHeavyStabilizationResult:
        if (restoration_resolver is None) == (restoration_resolver_factory is None):
            raise ValueError(
                "recovery-heavy stabilization requires exactly one of "
                "restoration_resolver or restoration_resolver_factory"
            )

        limit = int(max_iterations)
        if limit <= 0:
            raise ValueError("recovery-heavy stabilization max_iterations must be positive")

        pressure_resolver: RecoveryHeavyPressureResolver | None = None
        previous_state_signature: tuple[object, ...] | None = None
        iterations: list[RotationRecoveryHeavyStabilizationIteration] = []

        final_plan: RotationPlan | None = None
        final_replay: RotationRecoveryHeavyReplay | None = None

        for index in range(1, limit + 1):
            plan = generate(pressure_resolver)
            maximum_events = (
                tuple(maximum_event_resolver(plan, resource))
                if maximum_event_resolver is not None
                else ()
            )
            displayed_recovery_at = (
                displayed_recovery_resolver_factory(plan, resource)
                if displayed_recovery_resolver_factory is not None
                else None
            )
            active_restoration_resolver = (
                restoration_resolver_factory(plan)
                if restoration_resolver_factory is not None
                else restoration_resolver
            )
            assert active_restoration_resolver is not None
            replay = self.replay_service.replay(
                build=build,
                plan=plan,
                resource=resource,
                restoration_resolver=active_restoration_resolver,
                maximum_events=maximum_events,
                calculation_context=calculation_context,
                displayed_recovery_at=displayed_recovery_at,
            )
            heavy_signature = self._heavy_signature(plan)
            plan_signature = self._plan_signature(plan)
            minimum_resource, total_shortfall = self._resource_state(replay)
            hard_obligation_state = self._hard_obligation_state(
                resolver=hard_obligation_state_resolver,
                plan=plan,
                replay=replay,
            )
            state_signature: tuple[object, ...] = (
                plan_signature,
                heavy_signature,
                minimum_resource,
                total_shortfall,
                hard_obligation_state,
            )
            iteration = RotationRecoveryHeavyStabilizationIteration(
                iteration=index,
                plan=plan,
                replay=replay,
                heavy_signature=heavy_signature,
                plan_signature=plan_signature,
                minimum_resource=minimum_resource,
                total_shortfall=total_shortfall,
                hard_obligation_state=hard_obligation_state,
            )
            iterations.append(iteration)
            final_plan = plan
            final_replay = replay

            if previous_state_signature is not None and state_signature == previous_state_signature:
                return RotationRecoveryHeavyStabilizationResult(
                    plan=plan,
                    replay=replay,
                    iterations=tuple(iterations),
                    converged=True,
                    termination_reason=(
                        "stable_fixed_point"
                        if iteration.tracked_hard_obligations_satisfied
                        else "stable_no_legal_improvement"
                    ),
                )

            previous_state_signature = state_signature
            pressure_resolver = self.replay_service.pressure_resolver(
                replay=replay,
                maximum_amount=maximum_amount,
                trigger_fraction=trigger_fraction,
                reserve_assessment_resolver=reserve_assessment_resolver,
            )

        assert final_plan is not None
        assert final_replay is not None
        return RotationRecoveryHeavyStabilizationResult(
            plan=final_plan,
            replay=final_replay,
            iterations=tuple(iterations),
            converged=False,
            termination_reason="iteration_limit_reached",
        )

    @staticmethod
    def _heavy_signature(
        plan: RotationPlan,
    ) -> tuple[tuple[float, int, str | None, str | None], ...]:
        return tuple(
            (
                float(action.time_seconds),
                int(action.sequence),
                action.bar,
                action.name,
            )
            for action in plan.actions
            if action.kind is RotationActionKind.HEAVY_ATTACK
        )

    @staticmethod
    def _plan_signature(plan: RotationPlan) -> tuple[object, ...]:
        actions = tuple(
            (
                float(action.time_seconds),
                int(action.sequence),
                action.kind.value,
                action.name,
                action.bar,
            )
            for action in plan.actions
        )
        return (
            plan.character_name,
            plan.build_name,
            float(plan.duration_seconds),
            actions,
        )

    @staticmethod
    def _resource_state(replay: RotationRecoveryHeavyReplay) -> tuple[int, int]:
        timeline = replay.final_projection.run.timeline
        amounts = [int(timeline.starting_amount)]
        amounts.extend(int(event.after) for event in timeline.events)
        minimum_resource = min(amounts)
        return minimum_resource, int(timeline.total_shortfall)

    @staticmethod
    def _hard_obligation_state(
        *,
        resolver: RecoveryHardObligationStateResolver | None,
        plan: RotationPlan,
        replay: RotationRecoveryHeavyReplay,
    ) -> tuple[str, ...]:
        if resolver is None:
            return ()

        by_key: dict[str, str] = {}
        for raw in resolver(plan, replay):
            value = str(raw).strip()
            if not value:
                continue
            key = value.casefold()
            by_key.setdefault(key, value)
        return tuple(by_key[key] for key in sorted(by_key))


__all__ = [
    "RecoveryAwareRotationGenerator",
    "RecoveryDisplayedRecoveryResolverFactory",
    "RecoveryHardObligationStateResolver",
    "RecoveryMaximumEventResolver",
    "RecoveryRestorationResolverFactory",
    "RotationRecoveryHeavyStabilizationIteration",
    "RotationRecoveryHeavyStabilizationResult",
    "RotationRecoveryHeavyStabilizationService",
]
