from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from minmax.resource_costs import ResourceType
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
        """Whether the fixed-point state contains no tracked hard failure.

        Resource shortfall is always tracked directly by the stabilizer. Any other
        hard obligation is represented by the caller-supplied canonical obligation
        state. An absent obligation resolver therefore means only resource shortfall
        can be proven here; it does not imply unknown obligations are satisfied.
        """
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
    """Regenerate recovery-heavy rotations until the complete schedule state stabilizes.

    Each iteration generates a plan from the latest pressure resolver, replays all
    caller-verified heavy restores through the authoritative Phase 4 sustain path,
    then builds the next pressure resolver from that replayed timeline.

    Fixed-point convergence requires the semantic action schedule, heavy positions,
    replayed resource floor/shortfall, and caller-supplied hard-obligation state to
    remain unchanged. Repeating only the heavy list is not sufficient because a
    heavy can displace other casts or change whether a mandatory responsibility is
    still satisfied.

    A repeated complete state is classified separately from a valid fixed point. If
    tracked hard failures remain unchanged, the loop terminates as deterministic
    no-legal-improvement rather than pretending the resulting rotation is valid.

    The service never invents restoration amounts, reserve requirements, hard
    obligations, or a recovery threshold. Those remain explicit caller evidence. A
    hard iteration cap prevents oscillating policies from looping indefinitely.
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
        restoration_resolver: VerifiedRecoveryHeavyRestorationResolver,
        reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None,
        hard_obligation_state_resolver: RecoveryHardObligationStateResolver | None = None,
        max_iterations: int = 6,
    ) -> RotationRecoveryHeavyStabilizationResult:
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
            replay = self.replay_service.replay(
                build=build,
                plan=plan,
                resource=resource,
                restoration_resolver=restoration_resolver,
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
        return tuple(
            str(value).strip()
            for value in resolver(plan, replay)
            if str(value).strip()
        )
