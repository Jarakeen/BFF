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

    def __post_init__(self) -> None:
        if not isinstance(self.frontier, ExtremeSustainedDPSRuntimeStateFrontier):
            raise TypeError("runtime-state whole-plan adapter requires a runtime-state frontier")

    @property
    def axes(self) -> tuple[str, ...]:
        return ("runtime_state",)

    @property
    def choice_count(self) -> int:
        count = self.frontier.candidate_count
        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError("runtime-state choice_count must be an integer")
        return count

    @property
    def denominator_proven(self) -> bool:
        value = self.frontier.denominator_proven
        if not isinstance(value, bool):
            raise TypeError("runtime-state denominator_proven must be boolean")
        return value

    @property
    def omitted_scope(self) -> tuple[str, ...]:
        value = self.frontier.omitted_scope
        if not isinstance(value, tuple):
            raise TypeError("runtime-state omitted_scope must be a tuple")
        return value

    def choice_at(self, index: int):
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("runtime-state choice index must be an integer")
        if index < 0 or index >= self.choice_count:
            raise IndexError("runtime-state choice index out of range")
        return self.frontier.choices[index]


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
