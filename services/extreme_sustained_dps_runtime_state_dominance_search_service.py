from __future__ import annotations

"""Compose finite runtime-state families into proof-safe sustained-DPS ceilings."""

from dataclasses import dataclass
from pathlib import Path

from services.extreme_sustained_dps_finite_whole_plan_dominance_service import (
    ExtremeSustainedDPSFiniteWholePlanDominanceResult,
    ExtremeSustainedDPSFiniteWholePlanDominanceService,
)
from services.extreme_sustained_dps_runtime_state_frontier_service import (
    ExtremeSustainedDPSRuntimeStateFrontier,
)
from services.extreme_sustained_dps_runtime_state_whole_plan_evaluator_service import (
    ExtremeSustainedDPSRuntimeStateEvaluationScenario,
    ExtremeSustainedDPSRuntimeStateWholePlanEvaluator,
)


@dataclass(frozen=True)
class _RuntimeStateWholePlanAdapter:
    frontier: ExtremeSustainedDPSRuntimeStateFrontier

    @property
    def axes(self) -> tuple[str, ...]:
        return ("runtime_state",)

    @property
    def choice_count(self) -> int:
        return int(self.frontier.candidate_count)

    @property
    def denominator_proven(self) -> bool:
        return bool(self.frontier.denominator_proven)

    @property
    def omitted_scope(self) -> tuple[str, ...]:
        return tuple(self.frontier.omitted_scope)

    def choice_at(self, index: int):
        target = int(index)
        if target < 0 or target >= self.choice_count:
            raise IndexError("runtime-state choice index out of range")
        return self.frontier.choices[target]


class ExtremeSustainedDPSRuntimeStateDominanceSearchService:
    """Produce a finite-family runtime_state pruning ceiling through Combat Simulation."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        scenario: ExtremeSustainedDPSRuntimeStateEvaluationScenario,
        evaluator: ExtremeSustainedDPSRuntimeStateWholePlanEvaluator | None = None,
    ) -> None:
        self.scenario = scenario
        self.evaluator = evaluator or ExtremeSustainedDPSRuntimeStateWholePlanEvaluator(
            database_path,
            scenario=scenario,
        )

    def search(
        self,
        *,
        candidate_key: str,
        frontier: ExtremeSustainedDPSRuntimeStateFrontier,
    ) -> ExtremeSustainedDPSFiniteWholePlanDominanceResult:
        return ExtremeSustainedDPSFiniteWholePlanDominanceService.evaluate_indexed(
            candidate_key=candidate_key,
            frontier=_RuntimeStateWholePlanAdapter(frontier),
            evaluator=self.evaluator,
            required_duration_seconds=float(self.scenario.plan.duration_seconds),
            source="finite runtime-state whole-plan sustained-DPS dominance",
        )


__all__ = ["ExtremeSustainedDPSRuntimeStateDominanceSearchService"]
