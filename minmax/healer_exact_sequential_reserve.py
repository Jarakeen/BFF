from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .healer_demand_policy import HealerDemandPolicyAssessment
from .healer_exact_budget_reserve_decision import (
    HealerExactBudgetReserveDecisionResult,
    propose_healer_exact_budget_reserve_decision,
)
from .resource_timeline import ResourceTimelineResult
from .rotation_plan import RotationPlan
from .rotation_reserve_priority import ReserveProtectionPriority
from .rotation_reserve_replay import ResourceTimelineReplayInputs
from .rotation_window_resource_budget import RotationWindowResourceBudget


@dataclass(frozen=True)
class HealerExactSequentialReserveStep:
    """Exact replay inputs for one healer demand against the current schedule.

    The evaluator must build every field from the exact ``RotationPlan`` passed
    to it. This makes later windows observe earlier withholding decisions instead
    of reusing a stale timeline or reserve calculation from the original plan.
    """

    demand_assessment: HealerDemandPolicyAssessment
    timeline: ResourceTimelineResult
    budget: RotationWindowResourceBudget
    priorities: tuple[ReserveProtectionPriority, ...]
    replay_inputs: ResourceTimelineReplayInputs


HealerExactSequentialStepEvaluator = Callable[
    [RotationPlan, int],
    HealerExactSequentialReserveStep,
]


@dataclass(frozen=True)
class HealerExactSequentialReserveResult:
    """Ordered exact-replay healer decisions sharing one evolving plan."""

    original_plan: RotationPlan
    final_plan: RotationPlan
    decisions: tuple[HealerExactBudgetReserveDecisionResult, ...]


def propose_exact_sequential_healer_reserve_decisions(
    *,
    plan: RotationPlan,
    step_count: int,
    evaluate_step: HealerExactSequentialStepEvaluator,
) -> HealerExactSequentialReserveResult:
    """Apply exact-replay reserve decisions across ordered healer demands.

    Each step is recomputed against the plan produced by the previous exact
    decision. Demand windows may overlap, as staggered rescue mechanics do, but
    their start times must strictly increase so execution order is deterministic.

    A step that cannot repair its reserve is still recorded and its explicitly
    selected withholding adjustments remain visible. The caller can therefore
    distinguish "best allowed attempt" from a proven-safe mechanic response by
    inspecting ``decision.exact_protection.replayed_assessment.satisfied``.
    """

    count = int(step_count)
    if count < 0:
        raise ValueError("exact healer sequential reserve step count cannot be negative")

    current = plan
    decisions: list[HealerExactBudgetReserveDecisionResult] = []
    previous_start: float | None = None

    for index in range(count):
        step = evaluate_step(current, index)
        demand = step.demand_assessment.demand

        if previous_start is not None and demand.start_seconds <= previous_start:
            raise ValueError(
                "exact healer sequential demand starts must strictly increase: "
                f"{demand.name} starts at {demand.start_seconds:g}s after {previous_start:g}s"
            )

        decision = propose_healer_exact_budget_reserve_decision(
            plan=current,
            demand_assessment=step.demand_assessment,
            timeline=step.timeline,
            budget=step.budget,
            priorities=step.priorities,
            replay_inputs=step.replay_inputs,
        )
        decisions.append(decision)
        current = decision.decision.adjustment.adjusted_plan
        previous_start = demand.start_seconds

    return HealerExactSequentialReserveResult(
        original_plan=plan,
        final_plan=current,
        decisions=tuple(decisions),
    )
