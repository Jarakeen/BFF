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


@dataclass(frozen=True)
class RotationRecoveryHeavyStabilizationIteration:
    """One generate -> replay step in recovery-heavy schedule stabilization."""

    iteration: int
    plan: RotationPlan
    replay: RotationRecoveryHeavyReplay
    heavy_signature: tuple[tuple[float, str | None, str | None], ...]


@dataclass(frozen=True)
class RotationRecoveryHeavyStabilizationResult:
    """Bounded fixed-point result for recovery-heavy rotation generation."""

    plan: RotationPlan
    replay: RotationRecoveryHeavyReplay
    iterations: tuple[RotationRecoveryHeavyStabilizationIteration, ...]
    converged: bool


class RotationRecoveryHeavyStabilizationService:
    """Regenerate recovery-heavy rotations until the heavy schedule stabilizes.

    Each iteration generates a plan from the latest pressure resolver, replays all
    caller-verified heavy restores through the authoritative Phase 4 sustain path,
    then builds the next pressure resolver from that replayed timeline. Convergence
    is defined only by the scheduled heavy signature (time, bar, name), not by
    diagnostic text or unrelated plan metadata.

    The service never invents restoration amounts, reserve requirements, or a
    recovery threshold. Those remain explicit caller evidence. A hard iteration
    cap prevents oscillating pressure policies from looping indefinitely.
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
        max_iterations: int = 6,
    ) -> RotationRecoveryHeavyStabilizationResult:
        limit = int(max_iterations)
        if limit <= 0:
            raise ValueError("recovery-heavy stabilization max_iterations must be positive")

        pressure_resolver: RecoveryHeavyPressureResolver | None = None
        previous_signature: tuple[tuple[float, str | None, str | None], ...] | None = None
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
            signature = self._heavy_signature(plan)
            iterations.append(
                RotationRecoveryHeavyStabilizationIteration(
                    iteration=index,
                    plan=plan,
                    replay=replay,
                    heavy_signature=signature,
                )
            )
            final_plan = plan
            final_replay = replay

            if previous_signature is not None and signature == previous_signature:
                return RotationRecoveryHeavyStabilizationResult(
                    plan=plan,
                    replay=replay,
                    iterations=tuple(iterations),
                    converged=True,
                )

            previous_signature = signature
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
        )

    @staticmethod
    def _heavy_signature(
        plan: RotationPlan,
    ) -> tuple[tuple[float, str | None, str | None], ...]:
        return tuple(
            (
                float(action.time_seconds),
                action.bar,
                action.name,
            )
            for action in plan.actions
            if action.kind is RotationActionKind.HEAVY_ATTACK
        )
