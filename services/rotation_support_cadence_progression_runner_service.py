from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Protocol

from minmax.character_build.passive_grant import PassiveGrant
from minmax.rotation_ability_priority import AbilityPriorityList
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_effect_uptime_service import RotationEffectUptimeRequirement
from services.rotation_support_cadence_evaluation_service import (
    RotationSupportCadenceEvaluationContext,
)
from services.rotation_support_cadence_neighborhood_service import (
    RotationSupportCadenceNeighborhoodObligation,
)
from services.rotation_support_cadence_progression_service import (
    RotationSupportCadenceProgressionStep,
)
from services.rotation_sustain_service import RotationSustainProjection


class RotationSupportCadenceProgressionStopReason(str, Enum):
    NO_PROMOTION = "no_promotion"
    REPEATED_PLAN = "repeated_plan"
    MAX_ITERATIONS = "max_iterations"


class _ProgressionStepper(Protocol):
    def step(
        self,
        *,
        build: PlayerBuild,
        seed_plan: RotationPlan,
        seed_sustain: RotationSustainProjection,
        obligations: tuple[RotationSupportCadenceNeighborhoodObligation, ...],
        priorities: AbilityPriorityList | None = None,
        evaluation_context: RotationSupportCadenceEvaluationContext | None = None,
        effect_uptime_requirements: tuple[RotationEffectUptimeRequirement, ...] = (),
        passives: Iterable[PassiveGrant] = (),
        character_id: str | None = None,
    ) -> RotationSupportCadenceProgressionStep: ...


@dataclass(frozen=True)
class RotationSupportCadenceProgressionRun:
    """Bounded progressive search history and its final accepted rotation state."""

    initial_plan: RotationPlan
    initial_sustain: RotationSustainProjection
    final_plan: RotationPlan
    final_sustain: RotationSustainProjection
    steps: tuple[RotationSupportCadenceProgressionStep, ...]
    stop_reason: RotationSupportCadenceProgressionStopReason
    max_iterations: int

    @property
    def iterations(self) -> int:
        return len(self.steps)

    @property
    def proposed_promotions(self) -> int:
        """Number of steps that proposed an eligible next seed before runner guards."""
        return sum(1 for step in self.steps if step.advanced)

    @property
    def advanced_steps(self) -> int:
        """Number of unique promoted schedules actually accepted by the runner."""
        proposed = self.proposed_promotions
        if (
            self.stop_reason is RotationSupportCadenceProgressionStopReason.REPEATED_PLAN
            and self.steps
            and self.steps[-1].advanced
        ):
            return max(0, proposed - 1)
        return proposed

    @property
    def unresolved(self) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for step in self.steps:
            for raw in step.unresolved:
                value = str(raw or "").strip()
                if not value:
                    continue
                key = value.casefold()
                if key in seen:
                    continue
                seen.add(key)
                ordered.append(value)
        return tuple(ordered)


class RotationSupportCadenceProgressionRunnerService:
    """Run deterministic local cadence improvement with explicit convergence bounds.

    Each iteration delegates exactly one neighborhood/evaluation/ranking decision to
    the existing progression service. The promoted complete plan and its sustain
    projection become the next seed. Build-aware effect uptime requirements are
    forwarded on every iteration so the step can recompute fresh candidate evidence.

    The runner stops when no candidate is promoted, when a proposed next schedule has
    already been accepted earlier in this run, or when ``max_iterations`` is reached.
    A repeated schedule is not re-accepted: the last unique plan remains final. Plan
    repetition is based on executable schedule identity rather than assumptions or
    diagnostics, which may legitimately accumulate provenance between refinements.
    """

    def __init__(self, progression_service: _ProgressionStepper) -> None:
        self.progression_service = progression_service

    def run(
        self,
        *,
        build: PlayerBuild,
        seed_plan: RotationPlan,
        seed_sustain: RotationSustainProjection,
        obligations: tuple[RotationSupportCadenceNeighborhoodObligation, ...],
        max_iterations: int = 8,
        priorities: AbilityPriorityList | None = None,
        evaluation_context: RotationSupportCadenceEvaluationContext | None = None,
        effect_uptime_requirements: tuple[RotationEffectUptimeRequirement, ...] = (),
        passives: Iterable[PassiveGrant] = (),
        character_id: str | None = None,
    ) -> RotationSupportCadenceProgressionRun:
        limit = int(max_iterations)
        if limit <= 0:
            raise ValueError("support cadence progression max_iterations must be positive")

        passive_tuple = tuple(passives)
        current_plan = seed_plan
        current_sustain = seed_sustain
        seen = {self._schedule_signature(seed_plan)}
        steps: list[RotationSupportCadenceProgressionStep] = []
        stop_reason = RotationSupportCadenceProgressionStopReason.MAX_ITERATIONS

        for _ in range(limit):
            step = self.progression_service.step(
                build=build,
                seed_plan=current_plan,
                seed_sustain=current_sustain,
                obligations=obligations,
                priorities=priorities,
                evaluation_context=evaluation_context,
                effect_uptime_requirements=effect_uptime_requirements,
                passives=passive_tuple,
                character_id=character_id,
            )
            steps.append(step)

            if not step.advanced:
                stop_reason = RotationSupportCadenceProgressionStopReason.NO_PROMOTION
                break

            next_signature = self._schedule_signature(step.next_seed_plan)
            if next_signature in seen:
                stop_reason = RotationSupportCadenceProgressionStopReason.REPEATED_PLAN
                break

            seen.add(next_signature)
            current_plan = step.next_seed_plan
            current_sustain = step.next_seed_sustain

        return RotationSupportCadenceProgressionRun(
            initial_plan=seed_plan,
            initial_sustain=seed_sustain,
            final_plan=current_plan,
            final_sustain=current_sustain,
            steps=tuple(steps),
            stop_reason=stop_reason,
            max_iterations=limit,
        )

    @staticmethod
    def _schedule_signature(plan: RotationPlan) -> tuple[object, ...]:
        return (
            plan.character_name.casefold(),
            plan.build_name.casefold(),
            float(plan.duration_seconds),
            tuple(
                (
                    float(action.time_seconds),
                    int(action.sequence),
                    action.kind.value,
                    (action.name or "").casefold(),
                    action.bar or "",
                )
                for action in plan.actions
            ),
        )


__all__ = [
    "RotationSupportCadenceProgressionRun",
    "RotationSupportCadenceProgressionRunnerService",
    "RotationSupportCadenceProgressionStopReason",
]
